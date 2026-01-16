
import os

content = """{% extends 'base.html' %}

{% block title %}EMI Payments - ShopCredit{% endblock %}
{% block page_title %}{{ title }}{% endblock %}

{% block content %}
<!-- Filters -->
<div class="card mb-4">
    <div class="card-body">
        <form method="get" class="row g-3">
            <div class="col-md-4">
                <select name="status" class="form-select" onchange="this.form.submit()">
                    <option value="">All EMIs</option>
                    <option value="pending" {% if selected_status == "pending" %}selected{% endif %}>Pending</option>
                    <option value="paid" {% if selected_status == "paid" %}selected{% endif %}>Paid</option>
                    <option value="overdue" {% if selected_status == "overdue" %}selected{% endif %}>Overdue</option>
                </select>
            </div>
        </form>
    </div>
</div>

<!-- EMI Table -->
<div class="card">
    <div class="card-body p-0">
        <div class="table-responsive">
            <table class="table table-hover mb-0">
                <thead>
                    <tr>
                        <th>Order</th>
                        <th>EMI #</th>
                        <th>Amount</th>
                        <th>Due Date</th>
                        <th>Status</th>
                        <th>Action</th>
                    </tr>
                </thead>
                <tbody>
                    {% for emi in emis %}
                    <tr class="{% if emi.is_paid %}table-success{% elif emi.due_date < today %}table-danger{% endif %}">
                        <td>
                            <a href="{% url 'core:order_detail' emi.order.pk %}" class="text-decoration-none fw-bold">
                                {{ emi.order.order_number }}
                            </a>
                        </td>
                        <td>
                            <span class="badge bg-light text-dark border">
                                #{{ emi.installment_number }}
                            </span>
                        </td>
                        <td class="fw-bold">₹{{ emi.amount|floatformat:2 }}</td>
                        <td>{{ emi.due_date|date:"d M Y" }}</td>
                        <td>
                            {% if emi.is_paid %}
                            <span class="badge bg-success">✓ Paid</span>
                            {% elif emi.due_date < today %}
                            <span class="badge bg-danger">
                                {{ emi.due_date|timesince:today }} overdue
                            </span>
                            {% else %}
                            <span class="badge bg-warning text-dark">Pending</span>
                            {% endif %}
                        </td>
                        <td>
                            {% if not emi.is_paid %}
                            <a href="{% url 'core:emi_pay' emi.pk %}" class="btn btn-sm btn-primary">
                                💳 Pay Now
                            </a>
                            {% else %}
                            <span class="text-muted small">
                                <i class="bi bi-check-circle-fill text-success"></i>
                                {{ emi.paid_date|date:"d M" }}
                            </span>
                            {% endif %}
                        </td>
                    </tr>
                    {% empty %}
                    <tr>
                        <td colspan="6" class="text-center py-5">
                            <div class="mb-3" style="font-size: 2rem;">📝</div>
                            <h5 class="text-muted">No EMI payments found</h5>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
{% endblock %}
"""

with open(r'd:\Projects\Master-Architect\core\templates\core\emi_list_v2.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Successfully wrote emi_list_v2.html")
