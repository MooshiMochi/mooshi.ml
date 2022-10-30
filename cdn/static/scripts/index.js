const base_url = "https://cdn.mooshi.ml";

// const base_url = "http://192.168.0.11:8080";

function getCookie(name) {
  var nameEQ = name + "=";
  var ca = document.cookie.split(";");
  for (var i = 0; i < ca.length; i++) {
    var c = ca[i];
    while (c.charAt(0) == " ") c = c.substring(1, c.length);
    if (c.indexOf(nameEQ) == 0) return c.substring(nameEQ.length, c.length);
  }
  return null;
}

const btn_upload = document.getElementById("btn_upload");
btn_upload.addEventListener("click", () => {
  // console.log("Upload");

  const file = document.getElementById("file-input").files[0];
  console.log(file);

  if (file == null) {
    alert("Please select a file to upload");
    return;
  }
  const formData = new FormData();
  formData.append("file", file);

  fetch(`${base_url}/upload`, {
    method: "POST",
    body: formData,
  })
    .then((res) => res.json())
    .then((data) => {
      if (data.error != null) {
        alert(data.error);
      } else {
        window.location.replace(`${base_url}/`);
      }
    })
    .catch((err) => console.log(err));
});

const upload_span = document.getElementById("file-input-select");
const file_input = document.getElementById("file-input");
file_input.onchange = function () {
  const file = file_input.files[0];
  if (file != null) {
    upload_span.innerHTML = `SELECTED ${file.name}`;
  }
};

function fetch_users() {
  let cookie = getCookie("user");
  let decoded_cookie = atob(cookie.substring(1, cookie.length - 1));
  let json_cookie = JSON.parse(decoded_cookie);
  // console.log(json_cookie._id != "383287544336613385");
  if (json_cookie.id != "383287544336613385") {
    // console.log(json_cookie.id);
    // console.log("383287544336613385");
    // console.log("Not admin");
    return;
  }

  // console.log("Sending fetch request...");
  fetch(`${base_url}/users`, {
    method: "GET",
  })
    .then((res) => res.json())
    .then((data) => {
      // console.log(data);

      if (data.error != null) {
        alert(data.error);
        return;
      }
      const users = data.users;

      const users_ul = document.getElementById("users_ul");

      if (users == null) return;

      users.forEach((user) => {
        const li = document.createElement("li");

        const del_btn = document.createElement("button");
        const bg_btn = document.createElement("button");
        const a = document.createElement("a");

        a.innerText = `${user.username}#${user.discriminator}`;
        if (user.username == undefined || user.username == null) {
          a.innerText = user._id;
        }

        bg_btn.classList.add("btnV");

        del_btn.style.background = "url('/static/assets/delete.svg')";
        del_btn.style.backgroundSize = "cover";
        del_btn.style.backgroundRepeat = "no-repeat";
        del_btn.style.backgroundPosition = "center";

        del_btn.style.verticalAlign = "middle";

        del_btn.style.width = "15px";
        del_btn.style.height = "15px";
        del_btn.style.border = "none";
        del_btn.style.marginRight = "5px";
        del_btn.style.marginLeft = "6px";
        del_btn.style.cursor = "pointer";

        del_btn.addEventListener("click", () => {
          var choice = confirm(
            "Are you sure you want to remove access from this user?"
          );
          if (choice == true) {
            fetch(`${base_url}/delete?user_id=${user._id}`, {
              method: "DELETE",
            })
              .then((res) => res.json())
              .then((data) => window.location.replace(`${base_url}/`))
              .catch((err) => console.log(err));
          }
        });

        bg_btn.appendChild(a);

        li.appendChild(del_btn);
        li.appendChild(bg_btn);
        users_ul.appendChild(li);
      });
    });
}

function fetch_files() {
  fetch(`${base_url}/files`)
    .then((res) => res.json())
    .then((data) => {
      // console.log(data);

      if (data.error != null) {
        alert(data.error);
        return;
      }

      const files_ul = document.getElementById("files_ul");

      if (data.files != null) {
        data.files.forEach((file_url) => {
          const filename = file_url.split("/").slice(-1)[0];

          const li = document.createElement("li");
          const a = document.createElement("a");
          const img_btn = document.createElement("button");

          const del_btn = document.createElement("button");

          del_btn.style.background = "url('/static/assets/delete.svg')";
          del_btn.style.backgroundSize = "cover";
          del_btn.style.backgroundRepeat = "no-repeat";
          del_btn.style.backgroundPosition = "center";

          del_btn.style.verticalAlign = "middle";

          del_btn.style.width = "15px";
          del_btn.style.height = "15px";
          del_btn.style.border = "none";
          del_btn.style.marginRight = "5px";
          del_btn.style.marginLeft = "6px";
          del_btn.style.cursor = "pointer";

          del_btn.addEventListener("click", () => {
            var choice = confirm("Are you sure you want to delete this file?");
            if (choice == true) {
              fetch(`${base_url}/delete?filename=${filename}`, {
                method: "DELETE",
              })
                .then((res) => res.json())
                .then((data) => window.location.replace(`${base_url}/`))
                .catch((err) => console.log(err));
            }
          });

          img_btn.classList.add("btnV");

          a.href = file_url;
          a.target = "_blank";
          a.innerText = filename;

          img_btn.appendChild(a);

          li.appendChild(del_btn);
          li.appendChild(img_btn);

          files_ul.appendChild(li);
        });
      }
    })
    .catch((err) => console.log(err));
}

const dropdown_btn = document.getElementById("dropdown_btn");
if (dropdown_btn != null) {
  dropdown_btn.addEventListener("click", () => {
    const dropdown = document.querySelector(".dropdown");
    dropdown.classList.toggle("active");
  });
}

fetch_users();
fetch_files();
