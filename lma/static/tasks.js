(function() {
    var project = {id: /projects\/(\d+)/.exec(location.pathname)[1]};
    var collapsed_cookie = 'clps_' + project.id;
    var collapsed = Cookies.getJSON(collapsed_cookie) || {};
    var $tree = $('.tasks-tree');

    $('#btn-task-delete').click(function() {
        if(!confirm('Вы уверены? Будут удалены все подзадачи!')) return;
        $('#form-delete').submit()
    });

    $('#tabs-task').find('a[href=#task-subtask]').on('shown.bs.tab', function() {
        console.log('FOCUS!');
        $('#form-subtask').find('input[name=subject]').focus();
    });

    $tree.on('click', 'a.toggler', function(e) {
        var $this = $(this), $li = $this.closest('li'), id = $li.data('id');
        if($this.html() == '[+]') {
            $this.html('[&ndash;]');
            $li.find('ul').hide();
            collapsed[id] = 1;
        } else {
            $this.html('[+]');
            $li.find('ul').show();
            delete(collapsed[id]);
        }
        Cookies.set(collapsed_cookie, collapsed);
    });

    console.log(collapsed)
    for(var i in collapsed) {
        console.log($tree.find('[data-id=' + i + '] a.toggler').eq(0).click());
    }


})();