
import type { Server } from 'http';

declare class sockjs$Connection extends events$EventEmitter {
  readable: boolean;
  writable: boolean;
  remoteAddress: string;
  remotePort: number;
  address: {[string]: any};
  headers: {[string]: any};
  url: string;
  pathname: string;
  prefix: string;
  protocol: string;
  readyState: number;
  write(message: string): void;
  close(code: string, reason: string): void;
  end(): void;
}

declare type sockjs$ServerOptions = {
  sockjs_url?: string;
  prefix?: string;
  response_limit?: number;
  websocket?: boolean;
  jsessionid?: boolean;
  log?: (severity: string, message: string) => void;
  heartbeat_delay?: number;
  disconnect_delay?: number;
  disable_cors?: boolean;
};

declare class sockjs$Server extends events$EventEmitter {
  constructor(options?: sockjs$ServerOptions): void;
  installHandlers(server: Server): void;
}

declare module 'sockjs' {
  declare export type Connection = sockjs$Connection;

  declare module.exports: {
    createServer(options?: sockjs$ServerOptions): sockjs$Server;
  }
}
