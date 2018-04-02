//
//  index.js
//  dSVP (server)
//
//  Created by p2k on 28.03.18.
//  Copyright (c) 2018 Patrick "p2k" Schneider
//
//  Licensed under the EUPL
//
// @flow

import winston from 'winston';
import expressWinston from 'express-winston';
import express from 'express';
import sockjs from 'sockjs';
import redis from 'redis';
import bodyParser from 'body-parser';

import { promisifyAll } from 'bluebird';

import WorkerService from './worker.service';

promisifyAll(redis.RedisClient.prototype);
promisifyAll(redis.Multi.prototype);

const consoleTransport = new winston.transports.Console({
  colorize: true,
});

winston.configure({
  transports: [consoleTransport],
});

const { DSVP_REDIS_URL, PORT } = process.env;

if (DSVP_REDIS_URL != null) {
  winston.info(`Using database: ${DSVP_REDIS_URL}`);
  const db = redis.createClient(DSVP_REDIS_URL);
  const wsvc = new WorkerService(db);

  const sockServer = sockjs.createServer({ prefix: '/sock' });
  sockServer.on('connection', wsvc.connectWorker);

  const app = express();

  app.use(expressWinston.logger({
    transports: [consoleTransport],
  }));

  app.use(bodyParser.json());

  app.use(wsvc.handleRequest);

  const server = app.listen((PORT != null ? parseInt(PORT, 10) : 8080), '0.0.0.0');
  sockServer.installHandlers(server);
}
else {
  winston.error('Environment variables missing. Read the manual.');
}
