// Staged smoke endpoint: no database, credentials or live data.
// Netlify reads literal config exports during deploy post-processing.
import {createWorkshopEntry} from "../runtime/workshop-entry.mjs";
import {reply} from "../gateway/response.mjs";
import {unavailable} from "../projection/workshop-state.mjs";
export const config={
  path:"/api/v1/workshop",
  method:["GET"],
  rateLimit:{windowLimit:6,windowSize:60,aggregateBy:["ip","domain"]}
};
export default createWorkshopEntry({operation:"read",env:process.env,
  loadRuntime:async()=>async()=>reply(503,unavailable(),60)});
