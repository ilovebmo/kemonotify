// TODO: DISPLAY POSTS IN APP

const { invoke } = window.__TAURI__.tauri;
const { emit, listen } = window.__TAURI__.event;
const { isPermissionGranted, requestPermission, sendNotification } =
  window.__TAURI__.notification;
const { open } = window.__TAURI__.shell;

// Templates
const creatorDisplayTemplate = document.getElementById(
  "creator-display-template",
);
const selectedCreatorDisplayTemplate = document.getElementById("selected-creator-display-template");

// Other elements
const selectedCreatorDisplay = document.getElementById("selected-creator-display");
const allCreatorDisplay = document.getElementById("all-creator-display");
const forceSearchButton = document.getElementById("forced-search");
const loadingSpinner = document.getElementById("loading-spinner");
const creatorName = document.getElementById("creator-name");
const timeSelect = document.getElementById("time-select");
const newPosts = document.getElementById("new-posts");

let filterTimeout;
creatorName.addEventListener("input", () => {
  clearTimeout(filterTimeout);

  filterTimeout = setTimeout(() => {
    displayCreators(
      creatorsList.vector.filter((creator) => {
        return creator.name
          .toLowerCase()
          .includes(creatorName.value.toLowerCase());
      }),
    );
  }, 200);
});

forceSearchButton.onclick = function () {
  invoke("forced_search", {
    window: this,
    creatorHashmap: creatorsList.hashmap,
    toCheck: toCheckList,
  });
};

let toCheckList = Array(0);

const creatorsList = await invoke("get_creators_list");

listen("new-posts-event", (e) => {
  emit("time-check-event", {
    time_str: timeSelect.value,
    to_check: toCheckList,
  });
  e.payload.forEach(postNotification);

  // Doesn't work yet...
  e.payload.forEach(function(post) {
    let empty_new_post = selectedCreatorDisplayTemplate.cloneNode(true);
    let new_post_template = empty_new_post.content.querySelector("li");
    new_post_template.id = `new post by ${post.user} (${post.service})`;
    let new_post_button = new_post_template.querySelector("button");
    new_post_button.onclick = function () {
      new_post_template.remove();
    };
    new_post_template.appendChild(selected_button);
  
    let new_post_image = new_post_template.querySelector("img");
    new_post_image.src = `https://img.kemono.su/icons/${post.service}/${post.user}`;
    new_post_button.appendChild(new_post_image);
  
    let new_post_name = new_post_template.querySelector("p");
    new_post_name.textContent = `${post.user} (${post.service})`;
    new_post_button.appendChild(new_post_name);
  
    newPosts.appendChild(new_post_template);
  })
});

invoke("background_search", {
  window: this,
  creatorHashmap: creatorsList.hashmap,
  timeStr: timeSelect.value,
});

displayCreators();

async function displayCreators(list = creatorsList.vector) {
  allCreatorDisplay.innerHTML = "";

  for (let i = 0; i < 200; i++) {
    let creator = list[i];
    let emptyTemplate = creatorDisplayTemplate.cloneNode(true);

    let creator_element = emptyTemplate.content.querySelector("li");
    creator_element.id = creator.id;

    let image = emptyTemplate.content.querySelector("img");
    image.src = `https://img.kemono.su/icons/${creator.service}/${creator.id}`;
    image.alt = `${creator.name} (${creator.service})`;
    creator_element.appendChild(image);

    let text = emptyTemplate.content.querySelector("p");
    text.href = `https://kemono.su/${creator.service}/user/${creator.id}`;
    text.textContent = `${creator.name} (${creator.service})`;
    creator_element.appendChild(text);

    let input = emptyTemplate.content.querySelector("input");
    input.id = creator.id;
    if (toCheckList.includes(input.id)) {
      input.checked = true;
    }
    input.onchange = function () {
      if (toCheckList.includes(input.id)) {
        document.getElementById(`${creator.name} (${creator.service})`).remove();
        toCheckList.splice(toCheckList.indexOf(input.id, 0));
      } else {
        let empty_selected_creator_template = selectedCreatorDisplayTemplate.cloneNode(true);
        let selected_creator_template = empty_selected_creator_template.content.querySelector("li");
        selected_creator_template.id = `${creator.name} (${creator.service})`;
        let selected_button = selected_creator_template.querySelector("button");
        selected_button.onclick = function () {
          selected_creator_template.remove();
          input.checked = false;
          toCheckList.splice(toCheckList.indexOf(input.id, 0));
        };
        selected_creator_template.appendChild(selected_button);

        let selected_image = selected_creator_template.querySelector("img");
        selected_image.src = `https://img.kemono.su/icons/${creator.service}/${creator.id}`;
        selected_button.appendChild(selected_image);


        let selected_name = selected_creator_template.querySelector("p");
        selected_name.textContent = `${creator.name} (${creator.service})`;
        selected_button.appendChild(selected_name);

        selectedCreatorDisplay.append(selected_creator_template);
        toCheckList.push(input.id);
      }
    };
    creator_element.appendChild(input);

    let button = emptyTemplate.content.querySelector("button");
    button.onclick = function () {
      open(`https://kemono.su/${creator.service}/user/${creator.id}`);
    };
    creator_element.appendChild(button);

    allCreatorDisplay.append(creator_element);
  }

  loadingSpinner.style.display = "none";
}

async function postNotification(post) {
  let permissionGranted = await isPermissionGranted();
  if (!(await isPermissionGranted())) {
    const permission = await requestPermission();
    permissionGranted = permission === "granted";
  }

  if (permissionGranted) {
    sendNotification({
      title: post.title,
      icon: `https://img.kemono.su/icons/${post.service}/${post.user}`,
      body: post.content,
    });
  }
}
