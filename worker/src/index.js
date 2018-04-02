//
//  index.js
//  dSVP (worker)
//
//  Created by p2k on 28.03.18.
//  Copyright (c) 2018 Patrick "p2k" Schneider
//
//  Licensed under the EUPL
//
// @flow

import winston from 'winston';

import WorkerService from './worker.service';

winston.configure({
  transports: [new winston.transports.Console({
    colorize: true,
  })],
});

let { DSVP_SERVER_URL, DSVP_CLIENT_AUTH_TOKEN } = process.env;

if (DSVP_SERVER_URL == null || DSVP_CLIENT_AUTH_TOKEN == null) {
  if (process.argv.length < 3) {
    winston.error('Invalid usage. Please read the manual.');
    process.exit(1);
  }
  else {
    [DSVP_SERVER_URL, DSVP_CLIENT_AUTH_TOKEN] = process.argv;
  }
}

if (DSVP_SERVER_URL != null && DSVP_CLIENT_AUTH_TOKEN != null) {
  const sc = new WorkerService(DSVP_SERVER_URL, DSVP_CLIENT_AUTH_TOKEN);
  sc.connect();
}
