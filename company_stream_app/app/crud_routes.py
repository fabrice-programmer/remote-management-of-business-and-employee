# =====================
# COMPREHENSIVE CRUD OPERATIONS
# =====================

# =====================
# DEPARTMENT CRUD
# =====================
@routes.route('/admin/departments/create', methods=['GET', 'POST'])
@login_required
def create_department():
    require_admin()
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        lead = request.form.get('lead', '').strip()
        summary = request.form.get('summary', '').strip()
        status = request.form.get('status', 'Active').strip()

        if not name:
            flash('Department name is required.', 'danger')
            return redirect(url_for('routes.create_department'))

        if Department.query.filter_by(name=name).first():
            flash('A department with this name already exists.', 'danger')
            return redirect(url_for('routes.create_department'))

        department = Department(
            name=name,
            lead=lead,
            summary=summary,
            status=status
        )
        db.session.add(department)
        db.session.commit()
        flash(f'Department "{name}" created successfully.', 'success')
        return redirect(url_for('routes.departments'))

    return render_template('department_form.html', department=None, action='Create')


@routes.route('/admin/departments/<int:dept_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_department(dept_id):
    require_admin()
    department = Department.query.get_or_404(dept_id)

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        lead = request.form.get('lead', '').strip()
        summary = request.form.get('summary', '').strip()
        status = request.form.get('status', 'Active').strip()

        if not name:
            flash('Department name is required.', 'danger')
            return redirect(url_for('routes.edit_department', dept_id=dept_id))

        # Check if name is taken by another department
        existing = Department.query.filter_by(name=name).filter(Department.id != dept_id).first()
        if existing:
            flash('A department with this name already exists.', 'danger')
            return redirect(url_for('routes.edit_department', dept_id=dept_id))

        department.name = name
        department.lead = lead
        department.summary = summary
        department.status = status
        db.session.commit()
        flash(f'Department "{name}" updated successfully.', 'success')
        return redirect(url_for('routes.departments'))

    return render_template('department_form.html', department=department, action='Edit')


@routes.route('/admin/departments/<int:dept_id>/delete', methods=['POST'])
@login_required
def delete_department(dept_id):
    require_admin()
    department = Department.query.get_or_404(dept_id)

    # Check if department has employees
    employee_count = User.query.filter_by(department=department.name).count()
    if employee_count > 0:
        flash(f'Cannot delete department with {employee_count} employee(s). Move employees to another department first.', 'danger')
        return redirect(url_for('routes.departments'))

    dept_name = department.name
    db.session.delete(department)
    db.session.commit()
    flash(f'Department "{dept_name}" deleted successfully.', 'success')
    return redirect(url_for('routes.departments'))


# =====================
# EMPLOYEE CRUD
# =====================
@routes.route('/admin/employees/<int:employee_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_employee(employee_id):
    require_admin()
    employee = User.query.get_or_404(employee_id)

    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        department = request.form.get('department', '').strip()
        position = request.form.get('position', '').strip()
        hire_date = request.form.get('hire_date', '').strip()
        role = request.form.get('role', 'employee').strip()

        if not full_name or not email or not department or not position:
            flash('Please complete all required fields.', 'danger')
            return redirect(url_for('routes.edit_employee', employee_id=employee_id))

        # Check if email is taken by another user
        if email != employee.email and User.query.filter_by(email=email).first():
            flash('That email is already in use.', 'danger')
            return redirect(url_for('routes.edit_employee', employee_id=employee_id))

        if department not in department_names():
            flash('Invalid department selected.', 'danger')
            return redirect(url_for('routes.edit_employee', employee_id=employee_id))

        employee.full_name = full_name
        employee.email = email
        employee.phone = phone
        employee.department = department
        employee.position = position
        employee.hire_date = hire_date
        employee.role = role
        db.session.commit()
        flash(f'{full_name} updated successfully.', 'success')
        return redirect(url_for('routes.employee_detail', employee_id=employee_id))

    return render_template('employee_form.html', employee=employee, action='Edit', department_list=department_names())


@routes.route('/admin/employees/<int:employee_id>/delete', methods=['POST'])
@login_required
def delete_employee(employee_id):
    require_admin()
    employee = User.query.get_or_404(employee_id)
    employee_name = employee.full_name or employee.username

    # Check for related data
    task_count = EmployeeTask.query.filter_by(employee_id=employee_id).count()
    report_count = ReportDocument.query.filter_by(sender_id=employee_id).count()
    message_count = DirectMessage.query.filter(
        (DirectMessage.sender_id == employee_id) | (DirectMessage.recipient_id == employee_id)
    ).count()

    if task_count > 0 or report_count > 0 or message_count > 0:
        flash(f'Cannot delete employee with associated tasks, reports, or messages. Please remove these first.', 'danger')
        return redirect(url_for('routes.employee_detail', employee_id=employee_id))

    db.session.delete(employee)
    db.session.commit()
    flash(f'Employee "{employee_name}" deleted successfully.', 'success')
    return redirect(url_for('routes.departments'))


# =====================
# TASK CRUD
# =====================
@routes.route('/admin/tasks/<int:task_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    require_admin()
    task = EmployeeTask.query.get_or_404(task_id)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        description = request.form.get('description', '').strip()
        priority = request.form.get('priority', 'Normal').strip()
        status = request.form.get('status', 'To Do').strip()
        due_date = request.form.get('due_date', '').strip()

        if not title:
            flash('Task title is required.', 'danger')
            return redirect(url_for('routes.edit_task', task_id=task_id))

        task.title = title
        task.description = description
        task.priority = priority
        task.status = status
        task.due_date = due_date
        db.session.commit()
        flash(f'Task "{title}" updated successfully.', 'success')
        return redirect(url_for('routes.employee_detail', employee_id=task.employee_id))

    return render_template('task_form.html', task=task, action='Edit')


@routes.route('/admin/tasks/<int:task_id>/delete', methods=['POST'])
@login_required
def delete_task(task_id):
    require_admin()
    task = EmployeeTask.query.get_or_404(task_id)
    task_title = task.title
    employee_id = task.employee_id

    db.session.delete(task)
    db.session.commit()
    flash(f'Task "{task_title}" deleted successfully.', 'success')
    return redirect(url_for('routes.employee_detail', employee_id=employee_id))


# =====================
# REPORT CRUD
# =====================
@routes.route('/admin/reports/<int:report_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_report(report_id):
    require_admin()
    report = ReportDocument.query.get_or_404(report_id)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        message = request.form.get('message', '').strip()
        status = request.form.get('status', 'Sent').strip()

        if not title:
            flash('Report title is required.', 'danger')
            return redirect(url_for('routes.edit_report', report_id=report_id))

        report.title = title
        report.message = message
        report.status = status
        db.session.commit()
        flash(f'Report "{title}" updated successfully.', 'success')
        return redirect(url_for('routes.reports'))

    return render_template('report_form.html', report=report, action='Edit')


@routes.route('/admin/reports/<int:report_id>/delete', methods=['POST'])
@login_required
def delete_report(report_id):
    require_admin()
    report = ReportDocument.query.get_or_404(report_id)
    report_title = report.title

    # Delete file if exists
    if report.stored_filename:
        try:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], report.stored_filename)
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error deleting file: {e}")

    db.session.delete(report)
    db.session.commit()
    flash(f'Report "{report_title}" deleted successfully.', 'success')
    return redirect(url_for('routes.reports'))


# =====================
# COMPANY UPDATE CRUD
# =====================
@routes.route('/admin/updates/<int:update_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_update(update_id):
    require_admin()
    update = CompanyUpdate.query.get_or_404(update_id)

    if request.method == 'POST':
        title = request.form.get('title', '').strip()
        body = request.form.get('body', '').strip()
        department = request.form.get('department', 'Company-wide').strip() or 'Company-wide'

        if not title or not body:
            flash('Please enter both a title and update details.', 'danger')
            return redirect(url_for('routes.edit_update', update_id=update_id))

        update.title = title
        update.body = body
        update.department = department
        db.session.commit()
        flash(f'Update "{title}" updated successfully.', 'success')
        return redirect(url_for('routes.manager_dashboard'))

    return render_template('update_form.html', update=update, action='Edit', department_list=department_names())


@routes.route('/admin/updates/<int:update_id>/delete', methods=['POST'])
@login_required
def delete_update(update_id):
    require_admin()
    update = CompanyUpdate.query.get_or_404(update_id)
    update_title = update.title

    db.session.delete(update)
    db.session.commit()
    flash(f'Update "{update_title}" deleted successfully.', 'success')
    return redirect(url_for('routes.manager_dashboard'))


# =====================
# CHAT MESSAGE DELETE
# =====================
@routes.route('/admin/messages/<int:message_id>/delete', methods=['POST'])
@login_required
def delete_chat_message(message_id):
    require_admin()
    message = ChatMessage.query.get_or_404(message_id)
    department = message.department

    db.session.delete(message)
    db.session.commit()
    flash('Message deleted successfully.', 'success')
    return redirect(url_for('routes.chat', department=department))


# =====================
# DIRECT MESSAGE DELETE
# =====================
@routes.route('/admin/direct-messages/<int:message_id>/delete', methods=['POST'])
@login_required
def delete_direct_message(message_id):
    require_admin()
    message = DirectMessage.query.get_or_404(message_id)

    # Delete attached file if exists
    if message.stored_filename:
        try:
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], message.stored_filename)
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error deleting file: {e}")

    sender_id = message.sender_id
    db.session.delete(message)
    db.session.commit()
    flash('Direct message deleted successfully.', 'success')
    return redirect(request.referrer or url_for('routes.dashboard'))
