"""
==============================================================================
REPORTS APP - VIEWS
==============================================================================
PDF report generation using ReportLab.

Reports:
    - Invoice: Credit order invoice with EMI schedule
    - Risk Summary: Risk analysis report for all customers
    - Credit History: Transaction history for a user
    - Daily Summary: Daily business summary

Author: ShopCredit Development Team
==============================================================================
"""

import io
from datetime import date, timedelta
from decimal import Decimal

from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, FileResponse
from django.db.models import Sum, Count

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, 
    Image, HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT

from core.models import Order, OrderItem, EMISchedule, CreditTransaction
from accounts.models import CustomUser, Profile


# =============================================================================
# STYLE DEFINITIONS
# =============================================================================

def get_custom_styles():
    """Get custom styles for PDF generation."""
    styles = getSampleStyleSheet()
    
    # Title style
    styles.add(ParagraphStyle(
        name='CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#1a237e'),
        spaceAfter=30,
        alignment=TA_CENTER,
    ))
    
    # Subtitle
    styles.add(ParagraphStyle(
        name='Subtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.grey,
        alignment=TA_CENTER,
        spaceAfter=20,
    ))
    
    # Section header
    styles.add(ParagraphStyle(
        name='SectionHeader',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#1a237e'),
        spaceBefore=20,
        spaceAfter=10,
    ))
    
    # Info text
    styles.add(ParagraphStyle(
        name='InfoText',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.black,
    ))
    
    # Right aligned
    styles.add(ParagraphStyle(
        name='RightAligned',
        parent=styles['Normal'],
        fontSize=10,
        alignment=TA_RIGHT,
    ))
    
    return styles


def get_table_style():
    """Get standard table style."""
    return TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
    ])


# =============================================================================
# INVOICE GENERATION
# =============================================================================

@login_required
def generate_invoice(request, order_id):
    """
    Generate PDF invoice for an order.
    
    Includes:
    - Order details
    - Line items
    - EMI schedule
    - Payment status
    """
    order = get_object_or_404(Order, pk=order_id)
    
    # Access control
    user = request.user
    if user.role == 'shop_owner' and order.shop_owner != user:
        return HttpResponse('Access denied', status=403)
    
    # Create PDF buffer
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=1*cm, bottomMargin=1*cm)
    
    styles = get_custom_styles()
    elements = []
    
    # Header
    elements.append(Paragraph('💳 ShopCredit', styles['CustomTitle']))
    elements.append(Paragraph('Intelligent Digital Udhaar System', styles['Subtitle']))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1a237e')))
    elements.append(Spacer(1, 20))
    
    # Invoice Title
    elements.append(Paragraph(f'INVOICE', styles['SectionHeader']))
    elements.append(Paragraph(f'Order Number: {order.order_number}', styles['InfoText']))
    elements.append(Paragraph(f'Date: {order.order_date.strftime("%d %B %Y")}', styles['InfoText']))
    elements.append(Spacer(1, 20))
    
    # Party Details
    party_data = [
        ['From (Wholesaler)', 'To (Shop Owner)'],
        [
            f'{order.wholesaler.profile.business_name or order.wholesaler.username}\n'
            f'{order.wholesaler.email}\n'
            f'{order.wholesaler.phone or ""}',
            f'{order.shop_owner.profile.business_name or order.shop_owner.username}\n'
            f'{order.shop_owner.email}\n'
            f'{order.shop_owner.profile.business_address or ""}'
        ]
    ]
    party_table = Table(party_data, colWidths=[250, 250])
    party_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f5f5f5')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(party_table)
    elements.append(Spacer(1, 20))
    
    # Order Items
    elements.append(Paragraph('Order Items', styles['SectionHeader']))
    
    items_data = [['#', 'Product', 'Quantity', 'Unit Price', 'Total']]
    for idx, item in enumerate(order.items.all(), 1):
        items_data.append([
            str(idx),
            item.product_name,
            str(item.quantity),
            f'Rs.{item.unit_price:.2f}',
            f'Rs.{item.total_price:.2f}'
        ])
    
    # Add total row
    items_data.append(['', '', '', 'Total:', f'Rs.{order.total_amount:.2f}'])
    
    items_table = Table(items_data, colWidths=[40, 200, 70, 90, 100])
    items_table.setStyle(get_table_style())
    # Bold the total row
    items_table.setStyle(TableStyle([
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f5f5f5')),
    ]))
    elements.append(items_table)
    elements.append(Spacer(1, 20))
    
    # EMI Schedule
    emis = order.emi_schedules.all().order_by('installment_number')
    if emis.exists():
        elements.append(Paragraph('EMI Payment Schedule', styles['SectionHeader']))
        
        emi_data = [['EMI #', 'Amount', 'Due Date', 'Status']]
        for emi in emis:
            status = '✓ Paid' if emi.is_paid else ('⚠ Overdue' if emi.due_date < date.today() else 'Pending')
            emi_data.append([
                str(emi.installment_number),
                f'Rs.{emi.amount:.2f}',
                emi.due_date.strftime('%d %b %Y'),
                status
            ])
        
        emi_table = Table(emi_data, colWidths=[60, 100, 150, 100])
        emi_table.setStyle(get_table_style())
        elements.append(emi_table)
        elements.append(Spacer(1, 20))
    
    # Payment Summary
    paid = order.paid_amount()
    pending = order.pending_amount()
    
    summary_data = [
        ['Payment Summary', ''],
        ['Total Amount', f'Rs.{order.total_amount:.2f}'],
        ['Paid', f'Rs.{paid:.2f}'],
        ['Pending', f'Rs.{pending:.2f}'],
    ]
    summary_table = Table(summary_data, colWidths=[300, 200])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a237e')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('SPAN', (0, 0), (-1, 0)),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (-1, 1), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('PADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(summary_table)
    
    # Footer
    elements.append(Spacer(1, 30))
    elements.append(HRFlowable(width="100%", thickness=1, color=colors.grey))
    elements.append(Paragraph(
        f'Generated on {date.today().strftime("%d %B %Y")} | ShopCredit - Intelligent Digital Udhaar System',
        styles['Subtitle']
    ))
    
    # Build PDF
    doc.build(elements)
    
    # Prepare response
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Invoice_{order.order_number}.pdf"'
    
    return response


# =============================================================================
# RISK SUMMARY REPORT
# =============================================================================

@login_required
def risk_summary(request):
    """
    Generate risk summary report for all customers.
    
    Admin/Wholesaler only.
    """
    user = request.user
    
    if user.role == 'shop_owner':
        return HttpResponse('Access denied', status=403)
    
    # Get profiles
    if user.role == 'wholesaler':
        profiles = Profile.objects.filter(
            user__orders_placed__wholesaler=user
        ).distinct()
    else:
        profiles = Profile.objects.filter(user__role='shop_owner')
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    
    styles = get_custom_styles()
    elements = []
    
    # Header
    elements.append(Paragraph('Risk Summary Report', styles['CustomTitle']))
    elements.append(Paragraph(f'Generated: {date.today().strftime("%d %B %Y")}', styles['Subtitle']))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1a237e')))
    elements.append(Spacer(1, 20))
    
    # Summary stats
    low = profiles.filter(risk_category='low').count()
    medium = profiles.filter(risk_category='medium').count()
    high = profiles.filter(risk_category='high').count()
    
    summary_data = [
        ['Risk Distribution', ''],
        ['Low Risk', f'{low} customers'],
        ['Medium Risk', f'{medium} customers'],
        ['High Risk', f'{high} customers'],
        ['Total', f'{profiles.count()} customers'],
    ]
    
    summary_table = Table(summary_data, colWidths=[250, 250])
    summary_table.setStyle(get_table_style())
    elements.append(summary_table)
    elements.append(Spacer(1, 20))
    
    # High risk details
    if high > 0:
        elements.append(Paragraph('High Risk Customers (Attention Required)', styles['SectionHeader']))
        
        high_risk = profiles.filter(risk_category='high')
        hr_data = [['Customer', 'Business', 'Outstanding', 'Credit Score']]
        for p in high_risk:
            hr_data.append([
                p.user.username,
                p.business_name or '-',
                f'Rs.{p.current_outstanding:.0f}',
                str(p.credit_score)
            ])
        
        hr_table = Table(hr_data, colWidths=[100, 150, 100, 100])
        hr_table.setStyle(get_table_style())
        elements.append(hr_table)
    
    doc.build(elements)
    
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Risk_Summary_Report.pdf"'
    
    return response


@login_required
def risk_user_report(request, user_id):
    """Generate risk report for a specific user."""
    target_user = get_object_or_404(CustomUser, pk=user_id)
    
    # Similar to risk_summary but for one user
    # Redirect to risk_summary for now
    return risk_summary(request)


# =============================================================================
# CREDIT HISTORY REPORT
# =============================================================================

@login_required
def credit_history(request):
    """
    Generate credit history report.
    """
    user = request.user
    
    if user.role == 'shop_owner':
        transactions = CreditTransaction.objects.filter(user=user)
        title = f'Credit History - {user.profile.business_name or user.username}'
    elif user.role == 'wholesaler':
        transactions = CreditTransaction.objects.filter(order__wholesaler=user)
        title = f'Transaction History - {user.profile.business_name or user.username}'
    else:
        transactions = CreditTransaction.objects.all()
        title = 'System Credit History'
    
    transactions = transactions.order_by('-created_at')[:100]
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    
    styles = get_custom_styles()
    elements = []
    
    # Header
    elements.append(Paragraph(title, styles['CustomTitle']))
    elements.append(Paragraph(f'Generated: {date.today().strftime("%d %B %Y")}', styles['Subtitle']))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1a237e')))
    elements.append(Spacer(1, 20))
    
    # Account summary for shop owners
    if user.role == 'shop_owner':
        profile = user.profile
        summary_data = [
            ['Account Summary', ''],
            ['Credit Limit', f'Rs.{profile.credit_limit:.0f}'],
            ['Current Outstanding', f'Rs.{profile.current_outstanding:.0f}'],
            ['Available Credit', f'Rs.{profile.available_credit():.0f}'],
            ['Credit Score', str(profile.credit_score)],
        ]
        summary_table = Table(summary_data, colWidths=[250, 250])
        summary_table.setStyle(get_table_style())
        elements.append(summary_table)
        elements.append(Spacer(1, 20))
    
    # Transaction history
    elements.append(Paragraph('Transaction History', styles['SectionHeader']))
    
    if transactions.exists():
        txn_data = [['Date', 'Type', 'Amount', 'Description', 'Balance']]
        for txn in transactions:
            txn_data.append([
                txn.transaction_date.strftime('%d %b %Y'),
                txn.get_transaction_type_display(),
                f'Rs.{txn.amount:.2f}',
                txn.description[:30] + '...' if len(txn.description) > 30 else txn.description,
                f'Rs.{txn.balance_after:.2f}'
            ])
        
        txn_table = Table(txn_data, colWidths=[80, 60, 80, 180, 80])
        txn_table.setStyle(get_table_style())
        elements.append(txn_table)
    else:
        elements.append(Paragraph('No transactions found.', styles['InfoText']))
    
    doc.build(elements)
    
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Credit_History.pdf"'
    
    return response


@login_required
def credit_user_report(request, user_id):
    """Generate credit report for a specific user."""
    return credit_history(request)


# =============================================================================
# DAILY SUMMARY REPORT
# =============================================================================

@login_required
def daily_summary(request):
    """
    Generate daily business summary report.
    """
    user = request.user
    today = date.today()
    
    if user.role == 'wholesaler':
        orders = Order.objects.filter(wholesaler=user, order_date=today)
        emis = EMISchedule.objects.filter(order__wholesaler=user, paid_date=today)
        title = f'Daily Summary - {user.profile.business_name or user.username}'
    else:
        orders = Order.objects.filter(order_date=today)
        emis = EMISchedule.objects.filter(paid_date=today)
        title = 'Daily Business Summary'
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    
    styles = get_custom_styles()
    elements = []
    
    # Header
    elements.append(Paragraph(title, styles['CustomTitle']))
    elements.append(Paragraph(f'Date: {today.strftime("%d %B %Y")}', styles['Subtitle']))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#1a237e')))
    elements.append(Spacer(1, 20))
    
    # Today's summary
    new_orders = orders.count()
    total_sales = orders.aggregate(Sum('total_amount'))['total_amount__sum'] or 0
    payments_received = emis.aggregate(Sum('amount'))['amount__sum'] or 0
    
    summary_data = [
        ["Today's Summary", ''],
        ['New Orders', str(new_orders)],
        ['Total Sales', f'Rs.{total_sales:.0f}'],
        ['Payments Received', f'Rs.{payments_received:.0f}'],
    ]
    
    summary_table = Table(summary_data, colWidths=[250, 250])
    summary_table.setStyle(get_table_style())
    elements.append(summary_table)
    elements.append(Spacer(1, 20))
    
    # New orders list
    if orders.exists():
        elements.append(Paragraph("Today's Orders", styles['SectionHeader']))
        
        order_data = [['Order #', 'Customer', 'Amount', 'Status']]
        for o in orders:
            order_data.append([
                o.order_number,
                o.shop_owner.username,
                f'Rs.{o.total_amount:.0f}',
                o.get_status_display()
            ])
        
        order_table = Table(order_data, colWidths=[120, 150, 100, 100])
        order_table.setStyle(get_table_style())
        elements.append(order_table)
    
    doc.build(elements)
    
    buffer.seek(0)
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Daily_Summary_{today}.pdf"'
    
    return response
