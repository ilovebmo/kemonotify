// TODO: DISPLAY POSTS IN APP

const {invoke} =
window.__TAURI__.tauri;
const {emit, listen} =
window.__TAURI__.event;
const {isPermissionGranted, requestPermission, sendNotification} =
window.__TAURI__.notification;
const {open} =
window.__TAURI__.shell


const creatorDisplayTemplate = document.getElementById('creator-display-template');
const allCreatorDisplay = document.getElementById('all-creator-display');
const loadingSpinner = document.getElementById('loading-spinner');
const forceSearchButton = document.getElementById('force-search');
const creatorName = document.getElementById('creator-name');
const timeSelect = document.getElementById('time-select');

let filterTimeout;
creatorName.addEventListener('input', () => {
  clearTimeout(filterTimeout);

  filterTimeout = setTimeout(() => {
    displayCreators(creatorsList.vector.filter((creator) => {return creator.name.toLowerCase().includes(creatorName.value.toLowerCase());}));
  }, 200);
})

timeSelect.onclick = function() {
  invoke('forced-search', {creatorHashmap: creatorsList.hashmap, to_check: toCheckList});
}

let toCheckList = Array(0);

const creatorsList = await invoke('get_creators_list');

listen('new-posts-event', (e) => {
  emit('time-check-event', {time_str: timeSelect.value, to_check: toCheckList});
  e.payload.forEach(postNotification);
});

invoke('background_search', {theWindow: this, creatorHashmap: creatorsList.hashmap, timeStr: timeSelect.value});

displayCreators();

async function displayCreators(list=creatorsList.vector) {
  allCreatorDisplay.innerHTML = '';

  for (let i=0; i<200; i++) {
    let creator = list[i];
    let emptyTemplate = creatorDisplayTemplate.cloneNode(true);

    let creator_element = emptyTemplate.content.querySelector("li");
    creator_element.id = creator.id;

    let image = emptyTemplate.content.querySelector('img');
    image.src = `https://img.kemono.su/icons/${creator.service}/${creator.id}`;
    image.alt = `${creator.name} (${creator.service})`;
    creator_element.appendChild(image);

    let text = emptyTemplate.content.querySelector('p');
    text.href = `https://kemono.su/${creator.service}/user/${creator.id}`;
    text.textContent = `${creator.name} (${creator.service})`;
    creator_element.appendChild(text);

    let input = emptyTemplate.content.querySelector('input');
    input.id = creator.id;
    if (toCheckList.includes(input.id)) {
      input.checked = true;
    }
    input.onchange = function() {
      if (toCheckList.includes(input.id)) {
        toCheckList.splice(toCheckList.indexOf(input.id, 0));
      } else {
        toCheckList.push(input.id);
      }
    }
    creator_element.appendChild(input);

    let button = emptyTemplate.content.querySelector('button');
    button.onclick = function() {open(`https://kemono.su/${creator.service}/user/${creator.id}`)};
    creator_element.appendChild(button);

    allCreatorDisplay.append(creator_element);
  };

  loadingSpinner.style.display = "none";
};

async function postNotification(post, _i=0, _a=Array(0)) {
  let permissionGranted = await isPermissionGranted();
  if (! await isPermissionGranted()) {
    const permission = await requestPermission();
    permissionGranted = permission === 'granted';
  }

  if (permissionGranted) {
    sendNotification({title: post.title, icon: `https://img.kemono.su/icons/${post.service}/${post.user}`, body: post.content});
  }
}
