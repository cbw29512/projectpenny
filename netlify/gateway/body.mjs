// Streaming byte bound; no compressed bodies or implicit JSON coercion.
export async function boundedJson(request,max) {
  const type=request.headers.get("content-type")||"";
  const encoding=request.headers.get("content-encoding");
  const length=request.headers.get("content-length");
  if(!/^application\/json(?:;\s*charset=utf-8)?$/i.test(type) ||
     (encoding && encoding.toLowerCase()!=="identity")) return {error:415};
  if(length!==null && (!/^\d+$/.test(length) || Number(length)>max))
    return {error:413};
  if(!request.body) return {error:400};
  const reader=request.body.getReader();
  const chunks=[];
  let size=0;
  try {
    while(true) {
      const {done,value}=await reader.read();
      if(done) break;
      size+=value.byteLength;
      if(size>max) {
        // Do not wait for an untrusted sender to finish an oversized stream.
        void reader.cancel().catch(()=>{});
        return {error:413};
      }
      chunks.push(Buffer.from(value));
    }
    if(length!==null && size!==Number(length)) return {error:400};
    const text=new TextDecoder("utf-8",{fatal:true}).decode(Buffer.concat(chunks,size));
    return {value:JSON.parse(text)};
  } catch {
    return {error:400};
  } finally { reader.releaseLock(); }
}
