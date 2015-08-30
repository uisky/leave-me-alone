(function() {
    var $options = $('#form-options'), $ul = $('ul.tasks-list'), selected = null, task;

    function renderTaskLI(task) {
        var $deadline, $users, $subj, $description, $a;

        $li = $('<li>').data('id', task.id).addClass('li-' + task.status);
        if(selected == task.id) {
            $li.addClass('active')
        }
        if(task.assignee && task.assignee.id == current_user.id) {
            $li.addClass('my')
        }

        $deadline = $('<div class="deadline">');
        var now = new Date();
        if(task.deadline) {
            $deadline
                .append(sprintf('%02d.%02d', task.deadline.getDate(), task.deadline.getMonth() + 1))
                .attr('title', task.deadline.toLocaleString('ru'));
            if(task.status in {'open':1, 'progress':1, 'pause':1} && task.deadline <= now) {
                $deadline.addClass('late');
            }
        }

        $users = $('<div class="users">');
        if(task.assignee) {
            $a = $('<a>').attr('href', 'members/' + task.assignee.id + '/').html(task.assignee.name)
            $users.append($a);
        }

        $subj = $('<div class="subj">');
        $subj.append('<small>[' + task.status + ',' + task.importance + ']</small> ');
        $subj.append($('<strong>').append(task.subject));
        if(task.importance in IMPORTANCE) $subj.append(IMPORTANCE[task.importance].icon);
        if(task.character in CHARACTERS) $subj.append(CHARACTERS[task.character].icon)

        $subj.append(' <a href="#" class="action-edit" title="Редактировать"><i class="fa fa-pencil-square-o"></i></a>');

        $li.append($deadline).append($users).append($subj);

        if(task.description) {
            $description = $('<div class="description">').html(task.description_md);
            $li.append($description)
        }

        return $li;
    }

    // Мастеринг данных (приводим даты к типу Date)
    for(var id in Tasks) {
        Tasks[id].created = new Date(Tasks[id].created);
        if(Tasks[id].deadline != null) Tasks[id].deadline = new Date(Tasks[id].deadline);
    }

    // Рендер списка
    for(var id in Tasks) {
        task = Tasks[id];
        $li = renderTaskLI(task);
        $ul.append($li);
    }

    // События в списке
    $ul.on('click', '.action-edit', function(e) {
        e.preventDefault();
        var id = $(this).parents('li').data('id'), $modal = $('#modal-edit'), $form = $('#form-edit'),
            task = Tasks[id];

        $form.find('.edit-owner').html(task.user.name);
        $form.find('.edit-status').html(task.status);
        $form.find('[name=subject]').val(task.subject);
        $form.find('[name=description]').val(task.description);
        $form.find('[name=deadline]').data('DateTimePicker').date(task.deadline);
        $form.find('[name=importance]').val(task.importance);
        if(task.assignee) {
            $form.find('[name=assigned_id]').val(task.assignee.id);
        }

        $('#modal-edit').modal('show');
    });
})();
