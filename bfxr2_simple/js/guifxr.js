window.onload = function() {
  for (var i = 0; i < 6; i++) {
      var slider_attack_time = new Slider("#attack_time"+i, {
          id: "instanced_attack_time",
          min: 0,
          max: 0.33,
          range: false,
          step: 0.0033,
          value: 0.231,
          ticks: [0, 0.033, 0.066, 0.099, 0.132, 0.165, 0.198, 0.231, 0.264, 0.29700000000000004, 0.33]
        });
        slider_attack_time.sliderElem.className += " singleselect";
        slider_attack_time.sliderElem.getElementsByClassName("slider-tick-container")[0].children[7].classList.add('defaulttick');
  }

}

