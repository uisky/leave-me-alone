(function() {
    var World = [], worldWidth = 100, worldHeight = 50, live = false, ticker = null,
        $field = $('#life'), $btnPlayPause = $('#btn-play-pause');

    var World = {
        data: {},
        $field: null,
        $table: null,
        age: 0,
        $age: $('#life-age'),

        init: function($field) {
            var x, y, $tr;
            this.$field = $field;
            this.$field.empty();
            this.$table = $('<table>').appendTo(this.$field);
            for(y = 0; y < worldHeight; y++) {
                $tr = $('<tr>').appendTo(this.$table);
                for(x = 0; x < worldWidth; x++) {
                    $('<td>')
                        .attr('id', 'cell-' + this.getId(x, y))
                        .data('x', x).data('y', y)
                        .appendTo($tr);
                }
            }
            self = this;
            this.$table.on('click', 'td', function(e) {
                var $td = $(this), x = $td.data('x'), y = $td.data('y');
                if($td.hasClass('alive')) {
                    self.deleteCell(x, y);
                } else {
                    self.createCell(x, y);
                }
            });
        },
        getId: function(x, y) {
            if(x < 0) x = worldWidth + x;
            if(x >= worldWidth) x %= worldWidth;
            if(y < 0) y = worldHeight + y;
            if(y >= worldHeight) y %= worldHeight;
            return x + '_' + y;
        },
        getTd: function(x, y) {
            return $('#cell-' + this.getId(x, y));
        },
        isCell: function(x, y) {
            return (this.getId(x, y) in this.data) ? 1 : 0;
        },
        createCell: function(x, y) {
            var id = this.getId(x, y), $td = this.getTd(x, y);
            this.data[id] = {x: x, y: y, age: 0}
            $td.addClass('alive');
        },
        deleteCell: function(x, y) {
            var id = this.getId(x, y), $td = this.getTd(x, y);
            delete this.data[id];
            $td.removeClass('alive');
        },
    };

    function heartbeat() {
        var x, y, i, n, yield = [], kill = [];
        World.$age.html(++World.age);

        for(y = 0; y < worldHeight; y++) {
            for(x = 0; x < worldWidth; x++) {
                n = World.isCell(x-1, y-1) + World.isCell(x, y-1) + World.isCell(x+1, y-1) +
                    World.isCell(x-1, y) + World.isCell(x+1, y) +
                    World.isCell(x-1, y+1) + World.isCell(x, y+1) + World.isCell(x+1, y+1);

                if(!World.isCell(x, y) && n == 3) {
                    yield.push({x: x, y: y})
                } else if(World.isCell(x, y) && (n < 2 || n > 3)) {
                    kill.push({x: x, y: y});
                }
            }
        }
        for(i in yield) {
            World.createCell(yield[i].x, yield[i].y);
        }
        for(i in kill) {
            World.deleteCell(kill[i].x, kill[i].y);
        }
        if(yield.length == 0 && kill.length == 0) {
            stop();
        }
    }

    function start() {
        $btnPlayPause.removeClass('btn-success').addClass('btn-warning').html('<i class="fa fa-pause"></i>');
        ticker = setInterval(heartbeat, 200);
        live = true;
    }

    function stop() {
        $btnPlayPause.removeClass('btn-warning').addClass('btn-success').html('<i class="fa fa-play"></i>');
        clearInterval(ticker);
        live = false;
    }

    // Тулбар
    $btnPlayPause.click(function(e) {
        if(live) {
            stop();
        } else {
            start();
        }
    });

    $('#btn-dump-field').click(function(e) {
        console.log(World);
    });

    $('#btn-clear').click(function() { World.init($field) });

    World.init($field);
})();