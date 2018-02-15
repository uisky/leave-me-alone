(function() {
    var $tree = $('.tasks-tree > ul'), $taskCurrent = $tree.find('.task.active').closest('li');

    function ctrlEnterSubmit(e) {
        if(e.ctrlKey && (e.which == 10 || e.which == 13)) {
            $(this).submit();
        }
    }

    // Кнопка удаления задачи в редакторе
    $('#btn-task-delete').click(function() {
        if(!confirm('Вы уверены? Будут удалены все подзадачи!')) return;
        $('#form-delete').submit()
    });

    // Фокус на поле "Задача" при активации таба "Создать подзадачу"
    $('#tabs-task').find('a[href="#task-subtask"]').on('shown.bs.tab', function() {
        $('#form-subtask').find('input[name=subject]').focus();
    });

    // Переместить задачу
    chparentSelectTask = function(e) {
        e.preventDefault();
        $('#form-chparent input[name=parent_id]').val($(this).closest('li').data('id'));
        $('#form-chparent').submit();
    };
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
    };
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
        var $this = $(this), open_togglers = $tree.find('li').not('.collapsed').children('.toggler');
        if(open_togglers.length > 0) {
            open_togglers.click();
            $this.html('<i class="fa fa-plus"></i>');
        } else {
            $tree.find('li').children('.toggler').click();
            $this.html('<i class="fa fa-minus"></i>');
        }
    }).html(
        $tree.find('li').not('.collapsed').children('.toggler').length
            ? '<i class="fa fa-minus"></i>'
            : '<i class="fa fa-plus"></i>'
    );

    // Установка статуса
    $('#form-setstatus').on('click', 'button.setter', function(e) {
        $('#form-setstatus input[name=status]').val($(this).data('status'));
        $('#form-setstatus').submit();
    });

    // Разворачиваем ветку с текущей задачей
    $tree.find('.active').parents('li.collapsed').children('.toggler').click();

    // Комменты
    $('#tabs-task a[href="#task-comments"]').on('shown.bs.tab', function() {
        var $tab = $('#task-comments'), $tabHandle = $('#tabs-task a[href="#task-comments"]');

        /* Вызывается после загрузки комментариев */
        function init_comments() {
            var $comments = $('#comments'), $formEdit = $('#form-comment-edit'), $modalEdit = $('#modal-comment-edit'),
                $btnSubmit = $formEdit.find(':submit');

            // Убираем мигающий значок о новых комментариях
            $tree.find('.task.active .fa-comment').removeClass('new');

            // Обвес формы добавления комментария
            $tab.find('#form-comment').ajaxForm({
                success: function(data) {
                    if(data.error) {
                        alert(data.error);
                        return;
                    }

                    $tab.find('ul.comments').append(data);
                    $tab.find('div.comments-empty-message').hide();

                    // Увеличиваем счётчики комментариев, где надо:
                    // 1. Таб
                    var tabLabel = $tabHandle.text();
                    if(/\(\d+\)/.test(tabLabel)) {
                        tabLabel = tabLabel.replace(/\((\d+)\)/, function(str, n) { return '(' + (parseInt(n) + 1) + ')' });
                    } else {
                        tabLabel += '(1)';
                    }
                    $tabHandle.text(tabLabel);

                    // 2. Текущая задача
                    var $counter = $taskCurrent.find('.cnt-comments');
                    if(!$counter.length) {
                        $counter = $('<span class="cnt-comments"><i class="fa fa-comment"></i> 1</span>').appendTo($taskCurrent.find('.subj:first'));
                    } else {
                        $counter.html('<i class="fa fa-comment"></i> ' + (parseInt($counter.text()) + 1));
                    }
                },
                clearForm: true
            }).keypress(ctrlEnterSubmit);

            // Обвес формы редактирования комментария
            $formEdit.ajaxForm({
                beforeSubmit: function() {
                    if($formEdit.find('[name=body]').val() == '') return confirm('Удалить комментарий?');
                    return true;
                },
                success: function(data) {
                    if(data.error) {
                        alert(data.error);
                        return;
                    }
                    if(data.action == 'deleted') {
                        $comments.find('li[data-id=' + data.id + ']').remove();

                        // Уменьшаем счётчики комментариев
                        // 1. Таб
                        $tabHandle.text($tabHandle.text().replace(/\((\d+)\)/, function(str, n) { if(n <= 1) return ''; else return '(' + (n-1) + ')' }));

                        // 2. Текущая задача
                        var $counter = $taskCurrent.find('.cnt-comments'), n = parseInt($counter.text());
                        if(n > 1) {
                            $counter.html('<i class="fa fa-comment"></i> ' + (n - 1));
                        } else {
                            $counter.remove();
                        }

                    } else if(data.action == 'saved') {
                        $comments.find('li[data-id=' + data.id + '] .body').html(data.body_html);
                    } else {
                        alert('Случилось что-то странное.');
                        return;
                    }
                    $modalEdit.modal('hide');
                }
            }).keyup(function(e) {
                if($formEdit.find('[name=body]').val() == '') {
                    $btnSubmit.removeClass('btn-primary').addClass('btn-danger').text('Удалить комментарий');
                } else {
                    $btnSubmit.removeClass('btn-danger').addClass('btn-primary').text('Сохранить');
                }
            }).keypress(ctrlEnterSubmit);

            $modalEdit.on('shown.bs.modal', function(e) {
                var $li = $(e.relatedTarget).parents('li');

                $formEdit.attr('action', $li.data('url'))
                        .find('[name=body]')
                        .attr('disabled', true)
                        .attr('placeholder', 'Минуточку, комментарий загружается...');

                $.get({
                    url: $li.data('url'),
                    success: function(data) {
                        $formEdit.find('[name=body]')
                                .attr('disabled', false)
                                .attr('placeholder', 'Комментарий будет удалён!')
                                .val(data.body)
                                .keyup()
                                .focus();
                    }
                });
            });

        }

        var LOAD_COMMENTS_ONLY_ONCE = false;
        if(LOAD_COMMENTS_ONLY_ONCE) {
            if($tab.find('.wait-stub').length) {
                $tab.load($tab.data('url'), init_comments);
            }
        } else {
            $tab.html('<div class="wait-stub"><i class="fa fa-spinner fa-spin"></i></div>');
            $tab.load($tab.data('url'), init_comments);
        }
    });

    // История
    $('#tabs-task a[href="#task-history"]').on('shown.bs.tab', function() {
        var $tab = $('#task-history');
        $tab.html('<div class="wait-stub"><i class="fa fa-spinner fa-spin"></i></div>');
        $tab.load($tab.data('url'));
    });

    // Баги
    $('#tabs-task a[href="#task-bugs"]').on('shown.bs.tab', function() {
        var $tab = $('#task-bugs');
        $tab.html('<div class="wait-stub"><i class="fa fa-spinner fa-spin"></i></div>');
        $tab.load($tab.data('url'));
    })
})();