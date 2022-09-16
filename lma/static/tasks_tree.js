(function() {
    let $tree = $('.tasks-tree > ul'),
        $taskCurrent = $tree.find('.task.active').closest('li'),
        storage = window.localStorage;

    function ctrlEnterSubmit(e) {
        if(e.ctrlKey && (e.which === 10 || e.which === 13)) {
            $(this).submit();
        }
    }

    // Развешиваем toggler'ы
    let collapsed = JSON.parse(storage.getItem('tasks_collapsed')) || [];
    $tree.find('ul > li').each(function() {
        let $li = $(this);
        if($li.children('ul').length) {
            if(collapsed.indexOf(parseInt($li.data('id'))) !== -1) {
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
        storage.setItem('tasks_collapsed', JSON.stringify(collapsed));
    });

    // Свернуть/развернуть все
    $('#btn-toggle-collapsed').click(function() {
        var $this = $(this), open_togglers = $tree.find('ul > li').not('.collapsed').children('.toggler');
        if(open_togglers.length > 0) {
            open_togglers.click();
            $this.html('<i class="fa fa-plus"></i>');
        } else {
            $tree.find('ul > li').children('.toggler').click();
            $this.html('<i class="fa fa-minus"></i>');
        }
    }).html(
        $tree.find('ul > li').not('.collapsed').children('.toggler').length
            ? '<i class="fa fa-minus"></i>'
            : '<i class="fa fa-plus"></i>'
    );

    // Разворачиваем ветку с текущей задачей
    $tree.find('.active').parents('li.collapsed').children('.toggler').click();

    // Установка статуса
    $('#form-setstatus').on('click', 'button.setter', function(e) {
        $('#form-setstatus input[name=status]').val($(this).data('status'));
        $('#form-setstatus').submit();
    });

    // Указание ветки
    function initGit() {
        // Модалка указания GIT-ветки
        let modalSetGitBranch = document.getElementById('modal-set-git-branch');
        if (modalSetGitBranch) {
            modalSetGitBranch.addEventListener('shown.bs.modal', () => {
                $('#form-set-git-branch').find('input[name=git_branch]').focus();
            });
        }
    }
    initGit();

    // Комменты
    function initComments() {
        let $tab = $('#task-comments'),
            $tabHandle = $('#tabs-task a[href="#task-comments"]');

        /* Вызывается после загрузки комментариев */
        function init_content() {
            let $comments = $('#comments'),
                $formEdit = $('#form-comment-edit'),
                $modalEdit = $('#modal-comment-edit'),
                $btnSubmit = $formEdit.find(':submit'), btnSubmit = document.getElementById('comments-add-submit'),
                $elFormAddComment = $tab.find('#form-comment');

            // Убираем мигающий значок о новых комментариях
            $tree.find('.task.active .fa-comment').removeClass('new');

            // Обвес формы добавления комментария
            $elFormAddComment.ajaxForm({
                beforeSubmit: function(e) {
                    console.log(e, this);
                    btnSubmit.innerText = 'Минуточку...';
                },
                success: function(data) {
                    if(data.error) {
                        alert(data.error);
                        return;
                    }

                    $tab.find('ul.comments').append(data);
                    $tab.find('div.comments-empty-message').hide();

                    // Очищаем инпут с картинкой
                    let image = document.getElementById('comments-add-image');
                    if (image) image.value = null;

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
                    btnSubmit.innerText = 'Отправить';
                },
                clearForm: true
            }).keypress(ctrlEnterSubmit);

            // Детектор гит-веток при добавлении комментария
            let elTaAddComment = document.getElementById('comments-add-body'),
                elAddCommentGitWarning = document.getElementById('comments-add-gitwarning');
            const likeBranch = ['feature/', 'bugfix/', 'refactor/', '`feature/', '`bugfix/', '`refactor/']
            elTaAddComment.addEventListener('keyup', (e) => {
                for(let like of likeBranch) {
                    if(elTaAddComment.value.startsWith(like)) {
                        elAddCommentGitWarning.style.display = 'block';
                        return;
                    }
                }
                elAddCommentGitWarning.style.display = 'none';
            })

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

        $('#tabs-task a[href="#task-comments"]').on('shown.bs.tab', function() {
            if (!$tab.data('loaded')) {
                $tab.html('<div class="wait-stub"><i class="fa fa-spinner fa-spin"></i></div>');
                $tab.load($tab.data('url'), () => {
                    $tab.data('loaded', '1')
                    init_content();
                });
            }
        });
    }
    initComments();

    // История
    function initHistory() {
        $('#tabs-task a[href="#task-history"]').on('shown.bs.tab', function() {
            let $tab = $('#task-history');
            $tab.html('<div class="wait-stub"><i class="fa fa-spinner fa-spin"></i></div>');
            $tab.load($tab.data('url'));
        });

    }
    initHistory();

    // Редактирование задачи
    function initEditTask() {
        $('#tabs-task a[href="#task-edit"]').on('shown.bs.tab', function() {
            let $tab = $('#task-edit');
            if (!$tab.data('loaded')) {
                $tab.html('<div class="wait-stub"><i class="fa fa-spinner fa-spin"></i></div>');
                $tab.load($tab.data('url'), () => {
                    $tab.data('loaded', '1');

                    // Кнопка удаления задачи в редакторе
                    $('#btn-task-delete').click(function() {
                        if(!confirm('Вы уверены? Будут удалены все подзадачи!')) return;
                        $('#form-delete').submit()
                    });

                    // Перенести в другую доску
                    $('#form-sprint .act-select-sprint').on('click', function(e) {
                        $('#form-sprint button.act-select-sprint.btn-primary').removeClass('btn-primary').addClass('btn-secondary');
                        $(this).removeClass('btn-secondary').addClass('btn-primary');
                        $('#form-sprint [name=sprint_id]').val($(this).data('id'));
                    });

                    // Сменить родителя
                    let chparentSelectTask = function(e) {
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
                    let swapSelectTask = function(e) {
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

                });
            }
        });
    }
    initEditTask();

    // Создать подзадачу
    function initSubtask() {
        // Загрузка контента при активации таба
        function loadTab() {
            let $tab = $('#task-subtask');
            if (!$tab.data('loaded')) {
                $tab.html('<div class="wait-stub"><i class="fa fa-spinner fa-spin"></i></div>');
                $tab.load($tab.data('url'), () => {
                    $tab.data('loaded', '1')
                    $tab.find('[name=subject]').focus();
                });
            }
        }

        $('#tabs-task a[href="#task-subtask"]').on('shown.bs.tab', loadTab);
        if(window.task_id === null) loadTab();
    }
    initSubtask();



})();