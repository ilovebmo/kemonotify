const {invoke} =
window.__TAURI__.tauri;
const {emit, listen} =
window.__TAURI__.event;
const {isPermissionGranted, requestPermission, sendNotification} =
 window.__TAURI__.notification;


let getCreatorsBtn;
let ulNamesList;
let creatorNameInput;
let startButton;
let newPostsList;
let timeSelect;

let rustCreatorsList;
let creatorCheckList;

getCreatorsBtn = document.getElementById('get_creators');
ulNamesList = document.getElementById('ul_names');
creatorNameInput = document.getElementById('creator_name');
startButton = document.getElementById('start_searching');
newPostsList = document.getElementById('new_posts');
timeSelect = document.getElementById('times');

listen('test-event', (e) => {
  emit('recv-event', {time_s: timeSelect.value?? '5', list: creatorCheckList});
  console.log(e.payload);
  newPostsList.innerHTML = e.payload.message;
});

invoke('background_search', {theWindow: this, theChecklist: creatorCheckList});
emit('recv-event', {time: 5, list: creatorCheckList});

document.addEventListener('DOMContentLoaded', () => getCreatorsListAsHTML());
getCreatorsBtn.addEventListener('click', () => getCreatorsListAsHTML());

let searchTimeout;
creatorNameInput.addEventListener('input', function(e) {
  clearTimeout(searchTimeout);

  searchTimeout = setTimeout(() => {
    updateCreatorsShown(this.value);
  }, 200);
});

startButton.addEventListener('click', async () => {
  let permissionGranted = await isPermissionGranted();
  if (! await isPermissionGranted()) {
    const permission = await requestPermission();
    permissionGranted = permission === 'granted';
  }
  if (permissionGranted) {
    sendNotification('Tauri is awesome!');
    sendNotification({title: 'TAURI', body: 'Tauri is awesome!'});
  }
});

document.jsUpdateCheckList = async function(service, id) {
  console.log(creatorCheckList, service, id);
  creatorCheckList = await invoke('update_check_list', {jsCheckList: creatorCheckList, service: service, id: id});
  document.getElementById('checking_now').innerHTML = await invoke('get_list_of_names', {theChecklist: creatorCheckList, creatorList: rustCreatorsList});
};

async function getCreatorsListAsHTML(list=null) {
  ulNamesList.innerHTML = 'Loading...';

  if (list==null) {
    rustCreatorsList = await invoke('get_creators_list');
    list = rustCreatorsList;
  };
  ulNamesList.innerHTML = '';
  for (let i=0; i<20; i++) {
    ulNamesList.innerHTML += build_creator_div(list[i]);
  };
};

function build_creator_div(creator) {
  return `<li>
  <a href="https://kemono.su/${creator.service}/user/${creator.id}" target="_blank">
  <img src="https://img.kemono.su/icons/${creator.service}/${creator.id}" alt="${creator.name}" width="100" height="100">
  ${creator.name}
  </a>
  <input type="checkbox" id="${creator.id}" name="${creator.service}" onchange="jsUpdateCheckList(this.name, this.id);">
  </li>`;
};

async function updateCreatorsShown(name) {
  const search_result = await invoke('filter_by_name', {creatorList: rustCreatorsList, inputName: name});
  getCreatorsListAsHTML(search_result);
};
