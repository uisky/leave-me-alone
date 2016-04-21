/** Write The Fucking Code Plugin **/
(function() {
    var $cat = $('<div id="plugin-wtfc">').css({
        background: 'url(/static/plugins/wtfc/write-the-fucking-code.png)',
        position: 'fixed',
        bottom: '-400px', right: '50px',
        width: '245px', height: '400px',
        'z-index': 1000
    }).appendTo('body');

    var timer, DELAY = 1000 * 5;

    function rise() {
        $cat.animate({bottom: '10px'}, 1000, 'swing', function() {
            timer = setTimeout(sink, 1000);
        });
    }

    function sink() {
        $cat.animate({bottom: '-400px'}, 200, 'swing', function() {
            timer = setTimeout(rise, DELAY);
        });
    }

    timer = setTimeout(rise, DELAY);

    $cat.click(function() {
        clearTimeout(timer);
        $cat.hide();
    });

})();