# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.addons.http_routing.models.ir_http import slug



class EventEvent(models.Model):
    _inherit = "event.event"

    exhibitor_register_menu = fields.Boolean(
        string='Register as Exhibitor', compute='_compute_exhibitor_register_menu',
        readonly=False, store=True)
    exhibitor_register_menu_ids = fields.One2many(
        'website.event.menu', 'event_id', string='Exhibitors Register Menus',
        domain=[('menu_type', '=', 'exhibitor_register')])

    brand_id = fields.Many2one("res.brand", string="Brand")

    analytic_account_id = fields.Many2one('account.analytic.account', string='Analytic Account',
                                          help='Related Analytic Account', ondelete='restrict',
                                          check_company=True)
    default_product_ids = fields.Many2many('product.product', string="Default Products")

    @api.depends('event_type_id', 'website_menu', 'exhibitor_register_menu')
    def _compute_exhibitor_register_menu(self):
        for event in self:
            if event.event_type_id and event.event_type_id != event._origin.event_type_id:
                event.exhibitor_register_menu = event.event_type_id.exhibitor_register_menu
            elif event.website_menu and (event.website_menu != event._origin.website_menu or not event.exhibitor_register_menu):
                event.exhibitor_register_menu = True
            elif not event.website_menu:
                event.exhibitor_register_menu = False

    # ------------------------------------------------------------
    # WEBSITE MENU MANAGEMENT
    # ------------------------------------------------------------

    def toggle_exhibitor_register_menu(self, val):
        self.exhibitor_register_menu = val

    def _get_menu_update_fields(self):
        return super(EventEvent, self)._get_menu_update_fields() + ['exhibitor_register_menu']

    def _update_website_menus(self, menus_update_by_field=None):
        super(EventEvent, self)._update_website_menus(menus_update_by_field=menus_update_by_field)
        for event in self:
            if event.menu_id and (not menus_update_by_field or event in menus_update_by_field.get('exhibitor_register_menu')):
                event._update_website_menu_entry('exhibitor_register_menu', 'exhibitor_register_menu_ids', '_get_exhibitor_register_menu_entries')

    def _get_menu_type_field_matching(self):
        res = super(EventEvent, self)._get_menu_type_field_matching()
        res['exhibitor_register'] = 'exhibitor_register_menu'
        return res

    def _get_exhibitor_register_menu_entries(self):
        self.ensure_one()
        return [(_('Register as Exhibitor'), '/event/%s/exhibitors_register' % slug(self), False, 60, 'exhibitor_register')]
