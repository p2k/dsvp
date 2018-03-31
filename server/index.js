//
//  index.js
//  dSVP (server)
//
//  Created by p2k on 28.03.18.
//  Copyright (c) 2018 Patrick "p2k" Schneider
//
//  Licensed under the EUPL
//

import express from 'express';
import sockjs from 'sockjs';

import bodyParser from 'body-parser';
import { Form } from 'multiparty';

import WorkerService from './worker.service';

const wsvc = WorkerService();

const sockServer = sockjs.createServer({prefix: '/sock'});
sockServer.on('connection', fsvc.connectWorker);

const app = express();

app.use(bodyParser.json());

app.get('/', (req, res) => {
  res.json({ok: true});
});
app.post('/upload', (req, res) => {
  const form = new Form();
  form.on('part', function(part) {
    if (part.filename != null) {
      console.log(`Receiving file '${part.filename}'`);
      
    }
    else {
      part.resume();
    }
  });
  form.parse(req);
});
