(function() {
    var project = {id: /projects\/(\d+)/.exec(location.pathname)[1]};
    var collapsed_cookie = 'clps_' + project.id;
    var collapsed = Cookies.getJSON(collapsed_cookie) || {};
    var $tree = $('.tasks-tree');

    // Кнопка удаления задачи в редакторе
    $('#btn-task-delete').click(function() {
        if(!confirm('Вы уверены? Будут удалены все подзадачи!')) return;
        $('#form-delete').submit()
    });

    // Фокус на поле "Задача" при активации таба "Создать подзадачу"
    $('#tabs-task').find('a[href=#task-subtask]').on('shown.bs.tab', function() {
        $('#form-subtask').find('input[name=subject]').focus();
    });

    $('#form-subtask, #form-edit').keypress(function(e) {
        if(e.ctrlKey && e.which == 10) {
            $(this).submit();
        }
    });

    // Развешиваем toggler'ы
    $tree.find('li').each(function() {
        var $this = $(this), $toggler = $('<i class="toggler">');
        if($this.children('ul').length) {
            if($this.data('id') in collapsed) {
                $toggler.addClass('collapsed');
                $this.find('> ul').hide();
            }
            $this.append($toggler);
        }
    });

    // Разворачивание деревьев
    $tree.on('click', '.toggler', function(e) {
        e.preventDefault();
        var $this = $(this), $li = $this.closest('li'), id = $li.data('id');
        if($this.hasClass('collapsed')) {
            $this.removeClass('collapsed');
            $li.find('> ul').show();
            delete(collapsed[id]);
        } else {
            $this.addClass('collapsed');
            $li.find('> ul').hide();
            collapsed[id] = 1;
        }
        Cookies.set(collapsed_cookie, collapsed);
    });

    // Установка статуса
    $('#form-setstatus').on('click', 'button.setter', function(e) {
        $('#form-setstatus input[name=status]').val($(this).data('status'))
        $('#form-setstatus').submit();
    });

})();