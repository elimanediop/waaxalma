const INPUT_KEY="waaxalma.conferenceInputDeviceId";
const OUTPUT_KEY="waaxalma.conferenceMonitorOutputDeviceId";
const ENABLED_KEY="waaxalma.conferenceMonitorEnabled";
const CONFERENCE_OUTPUT_KEY="waaxalma.audioOutputDeviceId";
const enabled=document.getElementById("conferenceMonitorEnabled");
const output=document.getElementById("conferenceMonitorDevice");
const refresh=document.getElementById("refreshButton");
const status=document.getElementById("status");
const caps=document.getElementById("capabilities");
let inputManager=null,outputManager=null,audio=null;
function setStatus(message,warning=false){status.textContent=message;status.classList.toggle("warning",warning);}
function isEnabled(){return localStorage.getItem(ENABLED_KEY)==="true";}
function inputId(){return localStorage.getItem(INPUT_KEY)||"";}
function outputId(){return localStorage.getItem(OUTPUT_KEY)||"";}
async function ensureManagers(){
 if(!window.WaaxalmaConferenceInputManager)throw new Error("WaaxalmaConferenceInputManager is not available.");
 if(!window.WaaxalmaAudioOutputManager)throw new Error("WaaxalmaAudioOutputManager is not available.");
 if(!inputManager){inputManager=new window.WaaxalmaConferenceInputManager({onDeviceUnavailable:()=>{localStorage.removeItem(INPUT_KEY);stopMonitoring().catch(()=>{});}});await inputManager.start();}
 if(!outputManager){outputManager=new window.WaaxalmaAudioOutputManager({onFallback:()=>localStorage.removeItem(OUTPUT_KEY)});await outputManager.start();}
}
function renderOutputs(devices){
 output.innerHTML='<option value="">Default audio output</option>';
 devices.filter(d=>d.kind==="audiooutput"&&d.deviceId&&d.deviceId!=="default").forEach((d,i)=>{const o=document.createElement("option");o.value=d.deviceId;o.textContent=d.label||`Audio output ${i+1}`;output.appendChild(o);});
 const saved=outputId();output.value=Array.from(output.options).some(o=>o.value===saved)?saved:"";if(saved&&!output.value)localStorage.removeItem(OUTPUT_KEY);
}
async function stopMonitoring(){if(audio){try{audio.pause();outputManager?.unregisterMediaElement(audio);audio.srcObject=null;}catch(_){}audio=null;}if(inputManager?.isCapturing)await inputManager.stopCapture();}
async function startMonitoring(){
 await ensureManagers();const selectedInput=inputId();if(!selectedInput)throw new Error("Select a Conference Input first (for example CABLE-A Output).");
 const selectedOutput=outputId(),conferenceOutput=localStorage.getItem(CONFERENCE_OUTPUT_KEY)||"";
 if(selectedOutput&&conferenceOutput&&selectedOutput===conferenceOutput)throw new Error("Conference Monitor must not use Conference Output. Select your headphones/headset.");
 await inputManager.setInputDevice(selectedInput);const stream=await inputManager.startCapture();await outputManager.setOutputDevice(selectedOutput);
 audio=await outputManager.createAudioElement({autoplay:true,controls:false,muted:false});await outputManager.attachMediaStream(audio,stream);await audio.play();
 setStatus(`Conference Monitor is live: ${stream.getAudioTracks()[0]?.label||"conference input"} → ${output.selectedOptions[0]?.textContent||"default output"}.`);
}
async function apply(){enabled.checked=isEnabled();output.disabled=!enabled.checked;await stopMonitoring();if(!enabled.checked){setStatus("Conference monitoring is disabled. Enable it to hear Conference Input through your headphones.");return;}try{await startMonitoring();}catch(e){console.error("[ConferenceMonitor]",e);setStatus(e.message,true);}}
async function refreshOutputs(){await ensureManagers();refresh.disabled=true;try{renderOutputs(await navigator.mediaDevices.enumerateDevices());if(isEnabled())await apply();}finally{refresh.disabled=false;}}
enabled.addEventListener("change",async()=>{localStorage.setItem(ENABLED_KEY,enabled.checked?"true":"false");await apply();});
output.addEventListener("change",async()=>{output.value?localStorage.setItem(OUTPUT_KEY,output.value):localStorage.removeItem(OUTPUT_KEY);if(isEnabled())await apply();});
refresh.addEventListener("click",()=>refreshOutputs().catch(e=>setStatus(e.message,true)));
window.addEventListener("storage",e=>{if(e.key===INPUT_KEY||e.key===CONFERENCE_OUTPUT_KEY)apply().catch(()=>{});});
window.addEventListener("beforeunload",()=>{stopMonitoring().catch(()=>{});inputManager?.stop();outputManager?.stop();});
(async()=>{caps.textContent=`getUserMedia: ${navigator.mediaDevices?.getUserMedia?"yes":"no"} · enumerateDevices: ${navigator.mediaDevices?.enumerateDevices?"yes":"no"} · setSinkId: ${HTMLMediaElement.prototype.setSinkId?"yes":"no"}`;try{await ensureManagers();await refreshOutputs();await apply();}catch(e){console.error("[ConferenceMonitor] initialization failed",e);setStatus(e.message,true);}})();