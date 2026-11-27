// Staged smoke endpoint: no database, credentials or live data.
// Netlify reads literal config exports during deploy post-processing.
import {smoke} from "../runtime/workshop-smoke.mjs";
export const config={
  path:"/api/v1/workshop",
  method:["GET"],
  rateLimit:{windowLimit:6,windowSize:60,aggregateBy:["ip","domain"]}
};
export default smoke("read");
