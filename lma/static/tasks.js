(function() {
    var project = {id: /projects\/(\d+)/.exec(location.pathname)[1]};
    var $tree = $('.tasks-tree > ul');

    // Кнопка удаления задачи в редакторе
    $('#btn-task-delete').click(function() {
        if(!confirm('Вы уверены? Будут удалены все подзадачи!')) return;
        $('#form-delete').submit()
    });

    // Фокус на поле "Задача" при активации таба "Создать подзадачу"
    $('#tabs-task').find('a[href=#task-subtask]').on('shown.bs.tab', function() {
        $('#form-subtask').find('input[name=subject]').focus();
    });

    // Сабмит редакторов по Ctrl+Enter
    $('#form-subtask, #form-edit').keypress(function(e) {
        if(e.ctrlKey && e.which == 10) {
            $(this).submit();
        }
    });

    // Переместить задачу
    chparentSelectTask = function(e) {
        e.preventDefault();
        $('#form-chparent input[name=parent_id]').val($(this).closest('li').data('id'));
        $('#form-chparent').submit();
    }
    $('#btn-chparent').click(function(e) {
        $('#form-edit').hide();
        $('#form-chparent').show();
        $tree.on('click', 'a', chparentSelectTask);
    });
    $('#btn-chparent-cancel').click(function(e) {
        $('#form-edit').show();
        $('#form-chparent').hide();
        $tree.off('click', 'a', chparentSelectTask);
    });
    $('#btn-chparent-root').click(function(e) {
        $('#form-chparent input[name=parent_id]').val(0);
        $('#form-chparent').submit();
    });

    // Поменять местами
    swapSelectTask = function(e) {
        e.preventDefault();
        $('#form-swap input[name=sister_id]').val($(this).closest('li').data('id'));
        $('#form-swap').submit();
    }
    $('#btn-swap').click(function(e) {
        $('#form-edit').hide();
        $('#form-swap').show();
        $tree.on('click', 'a', swapSelectTask);
    });
    $('#btn-swap-cancel').click(function(e) {
        $('#form-edit').show();
        $('#form-swap').hide();
        $tree.off('click', 'a', swapSelectTask);
    });

    // Развешиваем toggler'ы
    var collapsed_cookie = 'clps';
    var collapsed = Cookies.getJSON(collapsed_cookie) || [];
    $tree.find('li').each(function() {
        var $li = $(this);
        if($li.children('ul').length) {
            if(collapsed.indexOf(parseInt($li.data('id'))) != -1) {
                $li.addClass('collapsed');
            }
            $li.append($('<i class="toggler">'));
        }
    });

    // Разворачивание деревьев
    $tree.on('click', '.toggler', function(e) {
        e.preventDefault();
        var $this = $(this), $li = $this.closest('li'), id = parseInt($li.data('id'));
        if($li.hasClass('collapsed')) {
            $li.removeClass('collapsed');
            collapsed.splice(collapsed.indexOf(id), 1);
        } else {
            $li.addClass('collapsed');
            collapsed.push(id);
        }
        Cookies.set(collapsed_cookie, collapsed, {expires: 365, path: ''});
    });

    // Свернуть/развернуть все
    $('#btn-toggle-collapsed').click(function() {
        var $this = $(this), open_togglers = $tree.children('li').not('.collapsed').children('.toggler');
        if(open_togglers.length > 0) {
            open_togglers.click()
            $this.html('<i class="fa fa-plus"></i>');
        } else {
            $tree.children('li').children('.toggler').click()
            $this.html('<i class="fa fa-minus"></i>');
        }
    }).html(
        $tree.children('li').not('.collapsed').children('.toggler').length
            ? '<i class="fa fa-minus"></i>'
            : '<i class="fa fa-plus"></i>'
    );

    // Установка статуса
    $('#form-setstatus').on('click', 'button.setter', function(e) {
        $('#form-setstatus input[name=status]').val($(this).data('status'))
        $('#form-setstatus').submit();
    });

    // Показать/скрыть готовое
    function hideDone() {
        if(Cookies.get('hide_done')) {
            $('.li-done').hide();
            $('#btn-toggle-done').html('<i class="fa fa-eye-slash"></i>').attr('title', 'Показать выполненные задачи');
        } else {
            $('.li-done').show()
            $('#btn-toggle-done').html('<i class="fa fa-eye"></i>').attr('title', 'Скрыть выполненные задачи');;
        }
    }
    $('#btn-toggle-done').click(function() {
        if(Cookies.get('hide_done')) {
            Cookies.remove('hide_done', {path: ''});
        } else {
            Cookies.set('hide_done', 1, {expires: 365, path: ''});
        }
        hideDone();
    });
    hideDone();

})();