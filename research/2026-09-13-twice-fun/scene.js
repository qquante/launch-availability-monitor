import * as THREE from './assets/vendor/three.module.min.js';
import { GLTFLoader } from './assets/vendor/GLTFLoader.js';
const host=document.getElementById('hero-scene');
const toggle=document.getElementById('motion-toggle');
let paused=matchMedia('(prefers-reduced-motion: reduce)').matches;
const setButton=()=>{toggle.setAttribute('aria-pressed',String(paused));toggle.setAttribute('aria-label',paused?'Play orbit animation':'Pause orbit animation');toggle.innerHTML=`<span class="icon"><svg viewBox="0 0 24 24" aria-hidden="true">${paused?'<path d="m8 5 11 7-11 7Z"/>':'<path d="M9 5v14M15 5v14"/>'}</svg></span>`};setButton();
toggle.addEventListener('click',()=>{paused=!paused;setButton()});
try{await startScene()}catch(error){console.warn('3D scene unavailable:',error.message);host.classList.add('fallback-active');toggle.hidden=true;}
async function startScene(){
const renderer=new THREE.WebGLRenderer({alpha:true,antialias:true,powerPreference:'low-power'});
renderer.setPixelRatio(Math.min(window.devicePixelRatio||1,2));renderer.setClearColor(0x000000,0);
renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.NeutralToneMapping;renderer.toneMappingExposure=1.0;
renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
const scene=new THREE.Scene();const camera=new THREE.PerspectiveCamera(36,1,.1,50);camera.position.set(0,.55,9.2);camera.lookAt(0,0,0);
scene.add(new THREE.HemisphereLight(0xf3fbff,0x144e38,1.05));
function light(color,intensity,x,y,z){const l=new THREE.DirectionalLight(color,intensity);l.position.set(x,y,z);scene.add(l);return l}
const key=light(0xffffff,2.9,-3,5,6);key.castShadow=true;key.shadow.mapSize.set(1024,1024);key.shadow.camera.left=-5;key.shadow.camera.right=5;key.shadow.camera.top=5;key.shadow.camera.bottom=-5;key.shadow.normalBias=.04;key.shadow.bias=-.0001;key.shadow.radius=4;
light(0x80dfff,.85,4,2,3);light(0x40f7a5,.28,1,-2,3);light(0xffffff,2.3,0,4,-3);
// A compact studio environment gives the physical mascot and token edges soft reflections.
const eW=128,eH=64,data=new Float32Array(eW*eH*4);
for(let y=0;y<eH;y++)for(let x=0;x<eW;x++){const u=x/eW,v=y/eH;const a=Math.exp(-(((u-.22)/.075)**2+((v-.34)/.12)**2))*3.5;const b=Math.exp(-(((u-.69)/.1)**2+((v-.4)/.18)**2))*1.6;const base=.16+.17*Math.max(0,1-v);const i=(y*eW+x)*4;data[i]=base+a+b*.87;data[i+1]=base+a+b;data[i+2]=base+a+b*1.04;data[i+3]=1;}
const envTexture=new THREE.DataTexture(data,eW,eH,THREE.RGBAFormat,THREE.FloatType);envTexture.mapping=THREE.EquirectangularReflectionMapping;envTexture.needsUpdate=true;
const pmrem=new THREE.PMREMGenerator(renderer);const env=pmrem.fromEquirectangular(envTexture);scene.environment=env.texture;envTexture.dispose();pmrem.dispose();
const mascotRig=new THREE.Group();scene.add(mascotRig);
const loader=new GLTFLoader();const gltf=await loader.loadAsync('/assets/twice-mascot.glb?v=2');const mascot=gltf.scene;
const box=new THREE.Box3().setFromObject(mascot);const size=box.getSize(new THREE.Vector3());const center=box.getCenter(new THREE.Vector3());
mascot.position.sub(center);const fit=3.28/Math.max(size.x,size.y);mascot.scale.multiplyScalar(fit);mascot.position.multiplyScalar(fit);mascotRig.add(mascot);mascotRig.position.y=.15;
mascot.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;if(o.material){const materials=Array.isArray(o.material)?o.material:[o.material];materials.forEach(m=>{if('envMapIntensity'in m)m.envMapIntensity=.5;})}}});
const shadow=new THREE.Mesh(new THREE.PlaneGeometry(7,4),new THREE.ShadowMaterial({color:0x267f68,opacity:.15}));shadow.rotation.x=-Math.PI/2;shadow.position.set(0,-1.67,-.2);shadow.receiveShadow=true;scene.add(shadow);
function orbitPoint(a){return new THREE.Vector3(2.88*Math.cos(a),.58*Math.sin(a)+.24*Math.cos(a)+.13,1.48*Math.sin(a));}
const orbitPoints=Array.from({length:181},(_,i)=>orbitPoint(i/180*Math.PI*2));
const orbit=new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(orbitPoints),new THREE.LineBasicMaterial({color:0x438f8c,transparent:true,opacity:.5}));scene.add(orbit);
const textureLoader=new THREE.TextureLoader();
async function coin(mark,baseColor,edgeColor){const group=new THREE.Group();const edge=new THREE.MeshStandardMaterial({color:edgeColor,roughness:.28,metalness:.5});const face=new THREE.MeshStandardMaterial({color:baseColor,roughness:.3,metalness:.06});const cylinder=new THREE.Mesh(new THREE.CylinderGeometry(.37,.37,.135,64),[edge,face,face]);cylinder.rotation.x=Math.PI/2;cylinder.castShadow=true;group.add(cylinder);
const rim=new THREE.Mesh(new THREE.TorusGeometry(.344,.017,12,80),new THREE.MeshStandardMaterial({color:baseColor,metalness:.25,roughness:.3}));rim.position.z=.075;group.add(rim);
const texture=await textureLoader.loadAsync(mark);texture.colorSpace=THREE.SRGBColorSpace;texture.anisotropy=renderer.capabilities.getMaxAnisotropy();
const aspect=(texture.image.naturalWidth||texture.image.width)/(texture.image.naturalHeight||texture.image.height);
const logo=new THREE.Mesh(new THREE.PlaneGeometry(.42*Math.min(1,aspect),.42/Math.max(1,aspect)),new THREE.MeshBasicMaterial({map:texture,transparent:true,depthWrite:false,side:THREE.DoubleSide,toneMapped:false}));logo.position.z=.082;group.add(logo);scene.add(group);return group;}
const [sol,rh]=await Promise.all([coin('/assets/solana.svg',0xffffff,0xc9dcd6),coin('/assets/robinhood.svg',0xccff00,0x9bbe25)]);
host.appendChild(renderer.domElement);host.classList.add('ready');
let pointerX=0,pointerY=0,elapsed=0,last=performance.now(),visible=true,raf;
host.addEventListener('pointermove',e=>{const r=host.getBoundingClientRect();pointerX=((e.clientX-r.left)/r.width-.5)*2;pointerY=((e.clientY-r.top)/r.height-.5)*2});host.addEventListener('pointerleave',()=>{pointerX=0;pointerY=0});
function resize(){const {width,height}=host.getBoundingClientRect();renderer.setSize(width,height,false);camera.aspect=width/Math.max(height,1);camera.position.z=Math.max(9.2,3.42/(Math.tan(THREE.MathUtils.degToRad(camera.fov/2))*camera.aspect)+.7);camera.updateProjectionMatrix();}const ro=new ResizeObserver(resize);ro.observe(host);resize();
function frame(stamp){raf=undefined;if(!visible||document.hidden)return;const dt=Math.min((stamp-last)/1000,.06);last=stamp;if(!paused)elapsed+=dt;const phase=elapsed*.32+.46;
sol.position.copy(orbitPoint(phase));rh.position.copy(orbitPoint(phase+Math.PI));
for(const [coin,angle] of [[sol,phase],[rh,phase+Math.PI]]){coin.rotation.set(.1*Math.cos(angle),.22*Math.sin(angle),.05*Math.sin(angle));}
mascotRig.position.y=.15+Math.sin(elapsed*1.2)*.055;const targetY=paused?0:pointerX*.13+Math.sin(elapsed*.6)*.035;const targetX=paused?0:pointerY*.055;mascotRig.rotation.y=THREE.MathUtils.lerp(mascotRig.rotation.y,targetY,.06);mascotRig.rotation.x=THREE.MathUtils.lerp(mascotRig.rotation.x,targetX,.06);
renderer.render(scene,camera);raf=requestAnimationFrame(frame);}
function resume(){last=performance.now();if(visible&&!document.hidden&&!raf)raf=requestAnimationFrame(frame)}
const io=new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;if(visible)resume();else if(raf){cancelAnimationFrame(raf);raf=undefined}},{threshold:.05});io.observe(host);document.addEventListener('visibilitychange',resume);resume();
renderer.domElement.addEventListener('webglcontextlost',e=>{e.preventDefault();host.classList.remove('ready');toggle.hidden=true;if(raf)cancelAnimationFrame(raf)});
window.addEventListener('pagehide',()=>{if(raf)cancelAnimationFrame(raf);io.disconnect();ro.disconnect();renderer.dispose();env.dispose();},{once:true});
}
