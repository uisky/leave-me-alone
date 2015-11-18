(function() {
    var $el = $('#plugin-1'), lunchtime = new Date();

    lunchtime.setHours(12);
    lunchtime.setMinutes(0);
    lunchtime.setSeconds(0);

    setInterval(function(){
        var now = new Date(), d = (lunchtime.valueOf() - now.valueOf()) / 1000,
            h = d / 3600 % 24, m = d / 60 % 60, s = d % 60;
        $el.html(sprintf('До обеда <b>%02d:%02d:%02d', h, m, s));
    }, 1000);

})();