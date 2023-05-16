# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


from odoo import _, api, exceptions, fields, models

import logging

_logger = logging.getLogger(__name__)

class CrmLead(models.Model):
    _inherit = "crm.lead"

    event_id = fields.Many2one('event.event', string='Event')


    def _prepare_customer_values(self, name, is_company=False, parent_id=False):
        """ Include Exhibtor Status."""
        values = super(CrmLead, self)._prepare_customer_values(
            name, is_company=is_company, parent_id=parent_id
        )
        values.update({
                "exhibitor_status": 'draft'
            })

        return values


    # Overridden: sale_crm
    def action_new_quotation(self):
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
            'default_event_id': self.event_id.id
        }
        if self.team_id:
            action['context']['default_team_id'] = self.team_id.id,
        if self.user_id:
            action['context']['default_user_id'] = self.user_id.id
        return action