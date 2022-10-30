// const base_url = "http://127.0.0.1:80";

const base_url = "http://192.168.0.11:80";

const btn_upload = document.getElementById("btn_upload");
btn_upload.addEventListener("click", () => {
  console.log("Upload");

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
    .then((data) => window.location.replace(`${base_url}/`))
    .catch((err) => console.log(err));
});

const upload_span = document.getElementById("file-input-select");
const file_input = document.getElementById("file-input");
file_input.onchange = function () {
  // console.log("File event triggered");
  const file = file_input.files[0];
  if (file != null) {
    upload_span.innerHTML = `SELECTED ${file.name}`;
  }
};

fetch(`${base_url}/files`)
  .then((res) => res.json())
  .then((data) => {
    console.log(data);

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
