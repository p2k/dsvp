//
//  worker.service.js
//  dSVP (worker)
//
//  Created by p2k on 28.03.18.
//  Copyright (c) 2018 Patrick "p2k" Schneider
//
//  Licensed under the EUPL
//

import { bind } from 'decko';

const BACKOFF_SCALE = [
  250,
  1000,
  2000,
  5000,
  10000
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
  constructor(url) {
    this._url = url;
    this._sock = null;
    this._retries = 0;
    this.connect();
  }

  @bind
  connect() {
    this._retries += 1;
    this._sock = new SockJS(DSVP_SERVER_URL);
    this._sock.onopen = this._onOpen;
    this._sock.onclose = this._onClose;
    this._sock.onmessage = this._onMessage;
  }

  @bind
  _onOpen() {
    console.log(`Connected to ${DSVP_SERVER_URL}`);
    this._retries = 0;
  }

  @bind
  _onClose() {
    const ms = getBackoff(this._retries);
    console.log(`Disconnected. Will reconnect in ${ms}ms`);
    this._sock.onopen = null;
    this._sock.onclose = null;
    this._sock.onmessage = null;
    this._sock = null;
    setTimeout(() => this.connect(), ms);
  }

  @bind
  _onMessage({ data }) {
    console.log('Received:', data);
    let action;
    try {
      action = JSON.parse(data);
    }
    catch (e) {
      console.log('Discarded message due to decode error');
      return;
    }


  }
}
