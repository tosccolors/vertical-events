# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import _, api, exceptions, fields, models

import logging

_logger = logging.getLogger(__name__)

class CrmLead(models.Model):
    _inherit = "crm.lead"

    event_id = fields.Many2one('event.event', string='Event')
    brand_id = fields.Many2one("res.brand", string="Brand")


    def _prepare_customer_values(self, name, is_company=False, parent_id=False):
        """ Include Exhibitor Status."""
        values = super(CrmLead, self)._prepare_customer_values(
            name, is_company=is_company, parent_id=parent_id
        )
        values.update({
                "user_id": False,
                "exhibitor_status": 'draft'
            })

        return values


    # Overridden: sale_crm
    def action_new_quotation(self):
        if self.event_id:
            action = self.env["ir.actions.actions"]._for_xml_id("website_event_exhibitors.sale_action_quotations_new")
        else:
            action = self.env["ir.actions.actions"]._for_xml_id("sale_crm.sale_action_quotations_new")

        action['context'] = {
            'search_default_opportunity_id': self.id,
            'default_opportunity_id': self.id,
            'search_default_partner_id': self.partner_id.id,
            'default_partner_id': self.partner_id.id,
            'default_campaign_id': self.campaign_id.id,
            'default_medium_id': self.medium_id.id,
            'default_origin': self.name,
            'default_source_id': self.source_id.id,
            'default_company_id': self.company_id.id or self.env.company.id,
            'default_tag_ids': [(6, 0, self.tag_ids.ids)],
            'default_event_id': self.event_id.id,
            'default_brand_id': self.event_id.brand_id and self.event_id.brand_id.id or False,
            'default_user_id': self.env.user.id,
            'default_website_id': self.event_id.website_id and self.event_id.website_id.id or False,
        }
        # Update: SO type as "Event SOT"
        if self.event_id:
            ref = self.env.ref
            action['context'].update({'default_type_id': ref('website_event_exhibitors.event_sale_type').id})
        return action

    def handle_partner_assignment(self, force_partner_id=False, create_missing=True):
        sponsor = self.env['event.sponsor']
        res = super().handle_partner_assignment(force_partner_id, create_missing)
        for lead in self:
            if not lead.event_id: continue
            # Update partner to Sponsor
            es = sponsor.search([('lead_id','=', lead.id)], limit=1, order='id desc')
            es.partner_id = lead.partner_id.id
        return res

    # Overridden (sale_crm)
    def action_view_sale_quotation(self):
        if self.event_id:
            action = self.env["ir.actions.actions"]._for_xml_id("website_event_exhibitors.action_quotations_event")
        else:
            action = self.env["ir.actions.actions"]._for_xml_id("sale.action_quotations_with_onboarding")
        action['context'] = {
            'search_default_draft': 1,
            'search_default_partner_id': self.partner_id.id,
            'default_partner_id': self.partner_id.id,
            'default_opportunity_id': self.id,
            'default_event_id': self.event_id.id,
            'default_brand_id': self.event_id.brand_id and self.event_id.brand_id.id or False,
            'default_website_id': self.event_id.website_id and self.event_id.website_id.id or False,
        }
        # Update: SO type as "Event SOT"
        if self.event_id:
            ref = self.env.ref
            action['context'].update({'default_type_id': ref('website_event_exhibitors.event_sale_type').id})

        action['domain'] = [('opportunity_id', '=', self.id), ('state', 'in', ['draft', 'sent'])]
        quotations = self.mapped('order_ids').filtered(lambda l: l.state in ('draft', 'sent'))
        if len(quotations) == 1:
            if self.event_id:
                action['views'] = [(self.env.ref('website_event_exhibitors.view_order_form').id, 'form')]
            else:
                action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
            action['res_id'] = quotations.id
        return action

    # Overridden (sale_crm)
    def action_view_sale_order(self):
        if self.event_id:
            action = self.env["ir.actions.actions"]._for_xml_id("website_event_exhibitors.action_orders_event")
        else:
            action = self.env["ir.actions.actions"]._for_xml_id("sale.action_orders")
        action['context'] = {
            'search_default_partner_id': self.partner_id.id,
            'default_partner_id': self.partner_id.id,
            'default_opportunity_id': self.id,
            'default_event_id': self.event_id.id,
            'default_brand_id': self.event_id.brand_id and self.event_id.brand_id.id or False,
            'default_website_id': self.event_id.website_id and self.event_id.website_id.id or False,
        }

        # Update: SO type as "Event SOT"
        if self.event_id:
            ref = self.env.ref
            action['context'].update({'default_type_id': ref('website_event_exhibitors.event_sale_type').id})

        action['domain'] = [('opportunity_id', '=', self.id), ('state', 'not in', ('draft', 'sent', 'cancel'))]
        orders = self.mapped('order_ids').filtered(lambda l: l.state not in ('draft', 'sent', 'cancel'))
        if len(orders) == 1:
            if self.event_id:
                action['views'] = [(self.env.ref('website_event_exhibitors.view_order_form').id, 'form')]
            else:
                action['views'] = [(self.env.ref('sale.view_order_form').id, 'form')]
            action['res_id'] = orders.id
        return action
