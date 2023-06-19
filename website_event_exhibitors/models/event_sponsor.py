# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _

import logging

_logger = logging.getLogger(__name__)


class StandType(models.Model):
    _name = 'event.stand.type'
    _order = 'sequence'

    name = fields.Char('Stand Type', required=True)
    sequence = fields.Integer(default=10)


class Sponsor(models.Model):
    _inherit = ["event.sponsor"]

    # Overridden:
    partner_id = fields.Many2one(string='Partner', tracking=True)
    name = fields.Char(string='Exhibitor Name')
    email = fields.Char(string='Exhibitor Email')
    phone = fields.Char(string='Exhibitor Phone')
    mobile = fields.Char(string='Exhibitor Mobile')

    # New
    visitor_id = fields.Many2one('website.visitor', string='Visitor', ondelete='set null')
    stand_number = fields.Char(string='Stand Number')
    stand_width = fields.Integer(string='Width (m)', help="Width of Stand in mtrs")
    stand_depth = fields.Integer(string='Depth (m)', help="Depth of Stand in mtrs")
    stand_surface_area = fields.Integer(string='Surface Area (sq.m)', compute='_compute_surface_area'
                                        , help="Surface Area for Stand in Sq mtrs", store=True)
    stand_type_id = fields.Many2one('event.stand.type', string='Stand Type', ondelete='set null')
    remarks = fields.Text('Remarks')
    prod_remarks = fields.Text('Products / Services')
    partner_company = fields.Char(string='Partner Company')
    lead_id = fields.Many2one('crm.lead', string='Lead')
    stand_construction = fields.Boolean('Include Stand Construction')

    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirm', 'Confirmed'),
        ('reject', 'Rejected')], string='Status',
        default='draft', copy=False, readonly=True, tracking=True)


    def _get_website_registration_allowed_fields(self):
        return {'name', 'phone', 'email', 'mobile', 'event_id', 'partner_id', 'stand_number'
                , 'stand_width', 'stand_depth', 'remarks', 'stand_type_id', 'partner_company'
                , 'prod_remarks'}

    @api.depends('stand_width', 'stand_depth')
    def _compute_surface_area(self):
        for case in self:
            case.stand_surface_area = case.stand_width * case.stand_depth


    def button_confirm(self):
        '''
            Confirm status of Partner from "Draft Exhibitor" to "Confirmed Exhibitor"
            Create Lead with information
        '''

        for case in self.filtered(lambda x: x.state == 'draft'):
            lead, partner = case.lead_id, False

            # Convert to Opportunity
            if lead.partner_id: partner = lead.partner_id
            else:
                partner = lead._find_matching_partner(email_only=True)
                lead.handle_partner_assignment(force_partner_id=partner.id)

            if not partner:
                lead.handle_partner_assignment(create_missing=True)
                partner = lead.partner_id
            lead.convert_opportunity(partner.id)
            lead.team_id = lead.event_id and lead.event_id.team_id.id or False
            lead.user_id = self.env.user

            # Update partner status
            if partner.exhibitor_status == 'draft':
                partner.exhibitor_status = 'confirmed'
                if partner.parent_id:
                    partner.parent_id.exhibitor_status = 'confirmed'

            case.write({'state': 'confirm'})
        return True

    def button_reject(self):
        for case in self.filtered(lambda x: x.state == 'draft'):
            case.lead_id.action_set_lost()
            case.write({'state': 'reject'})
        return True


    def action_open_leads(self):
        self.ensure_one()
        if not self.lead_id: return False

        return {
            'name': _('Lead'),
            'view_mode': 'form',
            'res_model': 'crm.lead',
            'res_id' : self.lead_id.id,
            'type': 'ir.actions.act_window',
            'context': {'create': False, 'active_test': False},
        }

    def action_open_sales(self):
        self.ensure_one()
        if not self.sale_ids: return False

        return {
            'name': _('Lead'),
            'view_mode': 'form',
            'res_model': 'crm.lead',
            'res_id' : self.lead_id.id,
            'type': 'ir.actions.act_window',
            'context': {'create': False, 'active_test': False},
        }


    def _create_lead(self):
        self.ensure_one()
        LeadObj = self.env['crm.lead']
        values = LeadObj.default_get(['type', 'stage_id'])
        publicUsr = self.env.ref('base.public_user').id
        if self.partner_id.id != publicUsr:
            values['partner_id'] = self.partner_id.id

        langID = self.env['res.lang']._lang_get_id(self._context.get('lang'))

        values.update({'type': 'lead',
                'contact_name': self.name,
                'email_from': self.email,
                'mobile': self.mobile,
                'phone': self.phone,
                'name': "Event: %s | %s" % (self.event_id.name, self.name),
                'partner_name': self.partner_company,
                'team_id': self.event_id.team_id.id or False,
                'event_id': self.event_id.id,
                'lang_id': langID,
                'brand_id': self.event_id.brand_id.id or False,
               })

        Lead = LeadObj.sudo().create(values)
        return Lead.id

    @api.model_create_multi
    def create(self, vals):
        res = super(Sponsor, self).create(vals)
        leadID = res._create_lead()
        res.lead_id = leadID
        return res





