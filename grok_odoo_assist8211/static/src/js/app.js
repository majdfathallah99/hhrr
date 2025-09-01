(function(){
  function byId(id){ return document.getElementById(id); }
  function add(role, text){
    var li=document.createElement('li');
    li.textContent = role + ": " + text;
    byId('log').appendChild(li);
  }
  async function send(){
    var text = byId('text').value || "";
    add("USER", text);
    byId('text').value = "";
    try{
      const res = await odoo.rpc({route:'/grok/send', params:{text:text, execute:true}});
      add("ASSISTANT", res.reply);
      if (res.results && res.results.length){
        add("ACTIONS", res.results.join(" | "));
      }
    }catch(e){
      add("ASSISTANT", "❌ حدث خطأ: " + (e && e.message ? e.message : e));
    }
  }
  document.addEventListener('DOMContentLoaded', function(){
    byId('send').addEventListener('click', send);
    byId('text').addEventListener('keydown', function(e){
      if (e.key === 'Enter'){ send(); }
    });
  });
})();