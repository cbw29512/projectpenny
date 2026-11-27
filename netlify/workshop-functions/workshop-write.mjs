// Staged smoke endpoint: no database, credentials or live data.
import {smoke} from "../runtime/workshop-smoke.mjs";
export const config={
  path:"/api/v1/bridge/workshop",
  method:["POST"],
  rateLimit:{windowLimit:3,windowSize:60,aggregateBy:["ip","domain"]}
};
export default smoke("write");
