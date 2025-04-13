window.onload = function() {
  var sliders_names=["attack_time0","attack_time1","attack_time2","attack_time3","attack_time4","attack_time5","global_vol"];
  for (var i = 0; i < sliders_names.length; i++) {
      var slider_attack_time = new Slider("#"+sliders_names[i], {
          id: "instanced_"+sliders_names[i],
          min: 0,
          max: 0.33,
          range: false,
          step: 0.0033,
          value: 0.231,
          ticks: [0, 0.033, 0.066, 0.099, 0.132, 0.165, 0.198, 0.231, 0.264, 0.29700000000000004, 0.33]
        });
        slider_attack_time.sliderElem.className += " singleselect";
        slider_attack_time.sliderElem.getElementsByClassName("slider-tick-container")[0].children[7].classList.add('defaulttick');
        if (sliders_names[i] == "global_vol") {
          //.slidernarrow
          slider_attack_time.sliderElem.classList.add('slidernarrow');
        }
  }
}

