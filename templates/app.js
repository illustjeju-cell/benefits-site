const $=s=>document.querySelector(s);let D=[],N=30;
function render(){const q=$("#q").value.trim(),f=$("#f").value,u=$("#u").value,t=$("#t").value,d=$("#d").value;
const L=D.filter(x=>(!q||(x.name+x.org+(x.summary||"")).includes(q))&&(!f||x.field===f)&&(!u||x.utype===u)&&(!t||x.stype===t)&&(!d||(d==="always"?x.dk==="always":(x.dk==="dated"&&x.dd!==null&&x.dd>=0&&x.dd<=+d))));
$("#cnt").textContent=L.length.toLocaleString()+"건";$("#more").style.display=L.length>N?"block":"none";
$("#list").innerHTML=L.slice(0,N).map(x=>`<a class="card" href="b/${x.id}.html"><div class="meta"><span class="st ${x.dk==="dated"&&x.dd!==null&&x.dd<=30&&x.dd>=0?"urgent":""}">${x.dl}</span><span>${x.org||""}</span></div><h2>${x.name}</h2><p class="sub">${x.field||""} · ${x.stype||""} · ${x.utype||""}</p><p class="sub">${x.summary||""}</p></a>`).join("")}
["#q","#f","#u","#t","#d"].forEach(s=>$(s).addEventListener("input",()=>{N=30;render()}));$("#more").onclick=()=>{N+=30;render()};
fetch("data.json").then(r=>r.json()).then(d=>{D=d;render()});
