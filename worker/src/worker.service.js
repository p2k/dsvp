//
//  worker.service.js
//  dSVP (worker)
//
//  Created by p2k on 28.03.18.
//  Copyright (c) 2018 Patrick "p2k" Schneider
//
//  Licensed under the EUPL
//
// @flow
//

import SockJS from 'sockjs-client';
import logger from 'winston';

import { bind } from 'decko';

const BACKOFF_SCALE = [
  250,
  1000,
  2000,
  5000,
  10000,
];

function getBackoff(retries) {
  if (retries < BACKOFF_SCALE.length) {
    return BACKOFF_SCALE[retries];
  }
  else {
    return BACKOFF_SCALE[BACKOFF_SCALE.length - 1];
  }
}

export default class WorkerService {
  _url: string;
  _authToken: string;
  _sock: ?SockJS;
  _retries: number;

  constructor(url: string, authToken: string) {
    this._url = url;
    this._authToken = authToken;

    this._sock = null;
    this._retries = 0;
  }

  @bind
  connect() {
    logger.info(`[WSVC] Connecting to: ${this._url}`);
    this._retries += 1;
    this._sock = new SockJS(this._url);
    this._sock.onopen = this._onOpen;
    this._sock.onclose = this._onClose;
    this._sock.onmessage = this._onMessage;
  }

  send(msg: {[string]: any}) {
    if (this._sock != null) {
      this._sock.send(JSON.stringify(msg));
    }
  }

  @bind
  _onOpen() {
    logger.info('[WSVC] Connection established. Authenticating...');
    this.send({ type: 'auth', token: this._authToken });
    this._retries = 0;
  }

  @bind
  _onClose() {
    const ms = getBackoff(this._retries);
    logger.info(`[WSVC] Disconnected. Will reconnect in ${ms}ms.`);
    if (this._sock != null) {
      this._sock.onopen = null;
      this._sock.onclose = null;
      this._sock.onmessage = null;
    }
    this._sock = null;
    setTimeout(() => this.connect(), ms);
  }

  @bind
  _onMessage({ data }: { data: string }) {
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
      logger.info(`[WSVC] Discarding invalid message: ${data}`);
      return;
    }

    logger.debug(`[WSVC] Received message: ${data}`);
    this.handleServerMessage(msg);
  }

  handleServerMessage(msg: {[string]: any}) {
    const sock = this._sock;
    if (sock == null) { // Assertion
      return;
    }

    switch (msg.type) {
      case 'auth':
        if (msg.result) {
          logger.info('Authenticated successfully.');
        }
        else {
          logger.error('Authentication failed. Retrying later.');
          this._retries = 999;
          sock.close();
        }
        break;
      case 'unknown':
        logger.warn(`[WSVC] Server asserts '${msg.sent_type}' is an unknown message!`);
        break;
      default:
        sock.send({ type: 'unknown', sent_type: msg.type });
    }
  }
}
