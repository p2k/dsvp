//
//  worker.service.js
//  dSVP (server)
//
//  Created by p2k on 28.03.18.
//  Copyright (c) 2018 Patrick "p2k" Schneider
//
//  Licensed under the EUPL
//
// @flow

import logger from 'winston';
import { Form } from 'multiparty';

import type { Connection } from 'sockjs';
import { Router } from 'express';
import type { $Request, $Response, NextFunction } from 'express';

import { bind } from 'decko';

const BASE64_RE = /^Bearer ((?:[A-Za-z0-9+/]{4})*(?:[A-Za-z0-9+/]{2}==|[A-Za-z0-9+/]{3}=)?)$/;
function getKeyFromHeader(req: $Request): ?string {
  const authorization = req.get('authorization');
  if (authorization == null) {
    return null;
  }
  const m = BASE64_RE.exec(authorization);
  if (m == null) {
    return null;
  }
  else {
    return Buffer.from(m[1], 'base64').toString('hex');
  }
}

function rejectAuth(res: $Response): boolean {
  res.append('WWW-Authenticate', 'Bearer realm="dsvp"');
  res.sendStatus(401);
  return false;
}

class WorkerConnection {
  _service: WorkerService;
  _conn: Connection;
  id: number;
  key: ?string;

  constructor(service: WorkerService, conn: Connection, connId: number) { // eslint-disable-line no-use-before-define
    this._service = service;
    this._conn = conn;
    this.id = connId;
    this.key = null;

    conn.on('data', this._onData);
    conn.on('close', this._onClose);
  }

  @bind
  _onClose() {
    logger.info(`[Worker#${this.id}] Disconnected.`);
    if (this.key != null) {
      this._service.setWorkerOnline(this.key, false);
    }
    this._conn.removeListener('data', this._onData);
    this._conn.removeListener('close', this._onClose);
    this._service.workerDisconnected(this.id);
  }

  @bind
  _onData(data: string) {
    let msg;
    try {
      msg = JSON.parse(data);
      if (typeof msg !== 'object') {
        throw new Error('not an object');
      }
      else if (msg == null) {
        throw new Error('null object');
      }
    }
    catch (e) {
      logger.info(`[Worker#${this.id}] Discarding invalid message: ${data}`);
      return;
    }

    logger.debug(`[Worker#${this.id}] Received message: ${data}`);
    this._handleMessage(msg);
  }

  _handleMessage(msg: {[string]: any}) {
    if (msg.type !== 'auth' && msg.type !== 'unknown' && !this.isAuthenticated) {
      this.send({ type: 'unauthorized', sent_type: msg.type });
      return;
    }

    switch (msg.type) {
      case 'auth':
        if (typeof msg.token === 'string') {
          const key = Buffer.from(msg.token, 'base64').toString('hex');
          if (key.length === 0) {
            this.send({ type: 'auth', result: false, reason: 'invalid_key' });
          }

          this.authenticate(key)
            .then((exists) => {
              if (exists) {
                logger.info(`[Worker#${this.id}] Worker authenticated with key: ${key}`);
                this.send({ type: 'auth', result: true });
                this._service.workerAuthenticated(this);
              }
              else {
                logger.warn(`[Worker#${this.id}] Worker with key '${key}' not found (sock)!`);
                this.send({ type: 'auth', result: false, reason: 'not_found' });
              }
            });
        }
        else {
          this.send({ type: 'auth', result: false, reason: 'invalid_key' });
        }
        break;
      case 'unknown':
        logger.warn(`[Worker#${this.id}] Worker asserts '${msg.sent_type}' is an unknown message!`);
        break;
      default:
        this.send({ type: 'unknown', sent_type: msg.type });
    }
  }

  authenticate(key: string): Promise<boolean> {
    return this._service.isWorkerInDB(key)
      .then((exists) => {
        this.key = key;
        this._service.setWorkerOnline(key, true);
        return exists;
      });
  }

  get isAuthenticated() {
    return this.key != null;
  }

  send(msg: {[string]: any}) {
    this._conn.write(JSON.stringify(msg));
  }
}

export default class WorkerService {
  _db: any;
  _nextWorkerId: number;
  _workers: Map<number, WorkerConnection>;
  _router: Router;

  constructor(db: any) {
    this._db = db;
    this._nextWorkerId = 1;
    this._workers = new Map();

    this._router = Router();
    // Free routes
    this._router.get('/', (req: $Request, res: $Response) =>
      res.json({ ok: true }));
    this._router.get('/favicon.ico', (req: $Request, res: $Response) =>
      res.sendStatus(404));

    // User routes
    this._router.post('/work/', this._checkUserAuth, (req) => {
      // Create work
    });

    // Worker routes
    this._router.route('/work/:unit/file')
      .all(this._checkWorkerAuth)
      .get((req) => {
        req.sendFile();
      })
      .post((req) => {
        const form = new Form();
        form.on('file', (name, file) => {
          logger.info(`[WSVC] Received result file: ${file.path}`);
        });
        form.parse(req);
      });
  }

  isWorkerInDB(key: string): Promise<boolean> {
    return this._db
      .existsAsync(`worker:${key}`)
      .then(exists => !!exists, () => false);
  }

  setWorkerOnline(key: string, online: boolean) {
    this._db.hsetAsync(`worker:${key}`, 'online', (online ? 'true' : 'false'));
  }

  isUserInDB(key: string): Promise<boolean> {
    return this._db
      .existsAsync(`user:${key}`)
      .then(exists => !!exists, () => false);
  }

  @bind
  connectWorker(conn: Connection) {
    this._workers.set(this._nextWorkerId, new WorkerConnection(this, conn, this._nextWorkerId));
    logger.info(`[WSVC] Connected #${this._nextWorkerId}`);
    this._nextWorkerId += 1;
  }

  workerAuthenticated(worker: WorkerConnection) {
    //Assign work
  }

  workerDisconnected(workerId: number) {
    this._workers.delete(workerId);
  }

  @bind
  handleRequest(req: $Request, res: $Response /* next: NextFunction */) {
    this._router(req, res, () => {
      // Catch-all
      res.sendStatus(404);
    });
  }

  @bind
  _checkWorkerAuth(req: $Request, res: $Response, next: NextFunction) {
    const key = getKeyFromHeader(req);
    if (key == null) {
      return rejectAuth(res);
    }

    this
      .isWorkerInDB(key)
      .then((exists) => {
        if (!exists) {
          logger.warn(`[WSVC] Worker with key '${key}' not found (http)!`);
          return rejectAuth(res);
        }
        next();
      })
      .catch(() =>
        res.sendStatus(500));
  }

  @bind
  _checkUserAuth(req: $Request, res: $Response, next: NextFunction) {
    const key = getKeyFromHeader(req);
    if (key == null) {
      return rejectAuth(res);
    }

    this
      .isUserInDB(key)
      .then((exists) => {
        if (!exists) {
          logger.warn(`[WSVC] User with key '${key}' not found (http)!`);
          return rejectAuth(res);
        }
        next();
      })
      .catch(() =>
        res.sendStatus(500));
  }
}
