//
//  index.js
//  dSVP (worker)
//
//  Created by p2k on 28.03.18.
//  Copyright (c) 2018 Patrick "p2k" Schneider
//
//  Licensed under the EUPL
//

import SockJS from 'sockjs-client';

import WorkerService from './worker.service';

let { DSVP_SERVER_URL, DSVP_CLIENT_ID } = process.env;

if (DSVP_SERVER_URL == null) {
  if (process.argv.length < 3) {
    console.error('Invalid usage. Please read the manual.');
    process.exit(1);
  }
  else {
    DSVP_SERVER_URL = process.argv[0];
    DSVP_CLIENT_ID = process.argv[1];
  }
}

const sc = new WorkerService(DSVP_SERVER_URL, DSVP_CLIENT_ID);
