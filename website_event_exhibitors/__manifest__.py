# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


{
    'name': 'Event Exhibitors Registration',
    'category': 'Marketing/Events',
    'sequence': 1005,
    'version': '14.0.9.0',
    'summary': 'Event: upgrade sponsors to exhibitors with registration',
    'author' : 'Deepa, The Open Source Company (TOSC)',
    'website': 'https://www.tosc.nl',
    'description': "",
    'depends': [
        'website_event_track_exhibitor',
        'website_event_track', 'google_recaptcha',
        'website_jitsi', 'crm', 'sale_crm', 'brand', 'sale_brand',
    ],
    'data': [
        'data/product_attribute.xml',
        'views/event_stand_views.xml',
        'views/event_event_views.xml',
        'views/event_sponsor_views.xml',
        'views/sale_order_views.xml',
        'views/event_exhibitor_templates_registration.xml',
        'views/event_exhibitor_templates_list.xml',
        "views/sale_report_template.xml",
        "views/invoice_report_template.xml",
        'security/ir.model.access.csv',
    ],
    'demo': [
    ],
    'application': False,
    'installable': True,
    'license': 'LGPL-3',
}
