// flow-typed signature: ee3fc98f640dcdb7d494c7a3eae18c7d
// flow-typed version: 68f2cdfa6a/sockjs-client_v1.x.x/flow_>=v0.25.x

type sockjs$Transport =
  | "jsonp-polling"
  | "xdr-streaming"
  | "xdr-polling"
  | "iframe-htmlfile"
  | "iframe-xhr-polling"
  | "xhr-streaming"
  | "xhr-polling"
  | "iframe-eventsource";

type sockjs$SessionIdGenerator = () => string;

type sockjs$SockJSOptions = {
  server?: string,
  transports?: sockjs$Transport | sockjs$Transport[],
  sessionId?: number | sockjs$SessionIdGenerator
};

declare class sockjs$SockJS extends WebSocket {
  constructor(
    url: string,
    _reserved?: null, // I'm not sure why and what for, but to prevent someone from using it as options it must be null or undefined
    options?: sockjs$SockJSOptions
  ): sockjs$SockJS;
}

declare module "sockjs-client" {
  declare module.exports: Class<sockjs$SockJS>;
}
