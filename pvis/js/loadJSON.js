function loadJSON(path, success, error) {
  var xhttpr = new XMLHttpRequest();
  xhttpr.onreadystatechange = function() {
    if (xhttpr.readyState === XMLHttpRequest.DONE) {
      if (xhttpr.status === 200) {
        if (success) success(JSON.parse(xhttpr.responseText));
      } else {
        if (error) error(xhttpr);
      }
    }
  };
  xhttpr.open("GET", path, true);
  xhttpr.send();
}
