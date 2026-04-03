(function () {
  function initTagInput(listId, hiddenId) {
    const list   = document.getElementById(listId);
    const hidden = document.getElementById(hiddenId);
    if (!list || !hidden) return;

    let tags = [];

    function render() {
      list.innerHTML = '';
      tags.forEach((tag, i) => {
        const pill = document.createElement('span');
        pill.className = 'tag-pill';
        pill.textContent = tag;
        const remove = document.createElement('button');
        remove.type = 'button';
        remove.textContent = '×';
        remove.onclick = () => { tags.splice(i, 1); render(); };
        pill.appendChild(remove);
        list.appendChild(pill);
      });
      const input = document.createElement('input');
      input.type = 'text';
      input.placeholder = 'Type and press Enter...';
      input.className = 'tag-input-field';
      input.onkeydown = (e) => {
        if (e.key === 'Enter') {
          e.preventDefault();
          const val = input.value.trim();
          if (val && !tags.includes(val)) { tags.push(val); render(); }
        }
      };
      list.appendChild(input);
      hidden.value = JSON.stringify(tags);
    }
    render();
  }

  document.addEventListener('DOMContentLoaded', () => {
    initTagInput('implemented-list', 'implemented_hidden');
    initTagInput('veto-list',        'veto_hidden');
  });
})();
