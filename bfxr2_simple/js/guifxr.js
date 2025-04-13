
function set_active_tab(tab_name) {
  var tab_page = document.getElementById("tab_page_"+tab_name);
  tab_page.classList.add("active_tab");
  var tab_buttons = document.getElementsByClassName("tab_button");
  for (var i = 0; i < tab_buttons.length; i++) {
    var tab_button = tab_buttons[i];  
    if (tab_button.id != "tab_button_"+tab_name) {
      tab_button.classList.remove("active_tab");
    } else if (!tab_button.classList.contains("active_tab")) {
      tab_button.classList.add("active_tab");
    }
  }
  var tab_pages = document.getElementsByClassName("tab_page");
  for (var i = 0; i < tab_pages.length; i++) {
    var tab_page = tab_pages[i];
    if (tab_page.id != "tab_page_"+tab_name) {
      tab_page.classList.remove("active_tab");
    } else if (!tab_page.classList.contains("active_tab")) {
      tab_page.classList.add("active_tab");
    }
  }
}