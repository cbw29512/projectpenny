// Staged smoke endpoint: no database, credentials or live data.
import {createWorkshopEntry} from "../runtime/workshop-entry.mjs";
import {reply} from "../gateway/response.mjs";
import {unavailable} from "../projection/workshop-state.mjs";
export const config={
  path:"/api/v1/bridge/workshop",
  method:["POST"],
  rateLimit:{windowLimit:3,windowSize:60,aggregateBy:["ip","domain"]}
};
export default createWorkshopEntry({operation:"write",env:process.env,
  loadRuntime:async()=>async()=>reply(503,unavailable(),60)});
