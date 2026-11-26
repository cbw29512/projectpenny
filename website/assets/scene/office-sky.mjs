// Low-precision orbital elements and perturbations: Paul Schlyter,
// https://stjarnhimlen.se/comp/ppcomp.html (sections 4–9).
// Original implementation for decorative scenery, not an almanac.
export const OFFICE_SKY = Object.freeze({zone:"America/New_York",latitude:35,longitude:-80});
const RAD=Math.PI/180, DAY=86400000;
const sin=x=>Math.sin(x*RAD), cos=x=>Math.cos(x*RAD);
const atan=(y,x)=>Math.atan2(y,x)/RAD;
const norm=x=>((x%360)+360)%360;
const asin=x=>Math.asin(Math.max(-1,Math.min(1,x)))/RAD;
const phases=Object.freeze(["New moon","Waxing crescent","First quarter","Waxing gibbous",
  "Full moon","Waning gibbous","Last quarter","Waning crescent"]);

function orbit(M,e) {
  // Solve Kepler's equation iteratively in degrees.
  M=norm(M);
  let E=M;
  for(let i=0;i<5;i++) E-=(E-e/RAD*sin(E)-M)/(1-e*cos(E));
  const x=cos(E)-e,y=Math.sqrt(1-e*e)*sin(E);
  return {v:atan(y,x),r:Math.hypot(x,y)};
}

function horizontal(lon,lat,obliquity,sidereal) {
  const x=cos(lon)*cos(lat),y=sin(lon)*cos(lat),z=sin(lat);
  const equY=y*cos(obliquity)-z*sin(obliquity);
  const equZ=y*sin(obliquity)+z*cos(obliquity);
  const ra=atan(equY,x),dec=atan(equZ,Math.hypot(x,equY));
  const h=norm(sidereal-ra+180)-180, p=OFFICE_SKY.latitude;
  return {alt:asin(sin(p)*sin(dec)+cos(p)*cos(dec)*cos(h)),hourAngle:h};
}

export function skyAt(ms) {
  try {
    if (!Number.isFinite(ms)||ms<Date.UTC(2000,0,1)||ms>=Date.UTC(2100,0,1)) return null;
    const d=(ms-Date.UTC(1999,11,31))/DAY;
    const ob=23.4393-3.563e-7*d;
    const Ms=norm(356.047+0.9856002585*d),ws=282.9404+4.70935e-5*d;
    const sunLon=norm(orbit(Ms,0.016709-1.151e-9*d).v+ws);
    const ut=norm((ms%DAY)/DAY*360);
    const sidereal=norm(Ms+ws+180+ut+OFFICE_SKY.longitude);
    const sun=horizontal(sunLon,0,ob,sidereal);
    const N=norm(125.1228-0.0529538083*d),w=318.0634+0.1643573223*d;
    const M=norm(115.3654+13.0649929509*d),i=5.1454;
    const moonOrbit=orbit(M,0.0549),u=moonOrbit.v+w;
    const x=cos(N)*cos(u)-sin(N)*sin(u)*cos(i);
    const y=sin(N)*cos(u)+cos(N)*sin(u)*cos(i),z=sin(u)*sin(i);
    const Lm=M+w+N,D=Lm-(Ms+ws),F=Lm-N;
    // Dominant lunar perturbations; decorative altitude remains approximate.
    const lon=norm(atan(y,x)-1.274*sin(M-2*D)+0.658*sin(2*D)-0.186*sin(Ms));
    const lat=atan(z,Math.hypot(x,y))-0.173*sin(F-2*D);
    const moon=horizontal(lon,lat,ob,sidereal);
    // Approximate topocentric altitude (lunar horizontal parallax).
    const distance=60.2666*moonOrbit.r-0.58*cos(M-2*D)-0.46*cos(2*D);
    moon.alt-=asin(cos(moon.alt)/distance);
    const phaseAngle=norm(lon-sunLon);
    const illumination=(1-cos(phaseAngle)*cos(lat))/2;
    const period=sun.alt>=6?"day":sun.alt>=-6?(sun.hourAngle<0?"dawn":"dusk")
      :sun.alt>=-12?"twilight":"night";
    return {period,sun,moon,phaseAngle,illumination,
      phase:phases[Math.round(phaseAngle/45)%8],
      moonVisible:moon.alt>1 && illumination>0.01,
      sunVisible:sun.alt>=-0.833};
  } catch { console.error("Office sky calculation unavailable."); return null; }
}
export function easternClock(ms) {
  try {
    if (!Number.isFinite(ms)||ms<Date.UTC(2000,0,1)||ms>=Date.UTC(2100,0,1)) return null;
    return new Intl.DateTimeFormat("en-US",{timeZone:OFFICE_SKY.zone,
      month:"short",day:"numeric",year:"numeric",hour:"numeric",minute:"2-digit",
      timeZoneName:"short"}).format(ms);
  } catch { return null; }
}
