# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.


import werkzeug
from werkzeug.exceptions import NotFound, Forbidden

from odoo import exceptions, http, fields
from odoo.addons.website_event_track.controllers.event_track import EventTrackController
from odoo.http import request

import logging

_logger = logging.getLogger(__name__)

class ExhibitorRegisterController(EventTrackController):

    # ------------------------------------------------------------
    # MAIN PAGE
    # ------------------------------------------------------------

    @http.route(['/event/<model("event.event"):event>/exhibitors_register'], type='http', auth="public", website=True, sitemap=False)
    def event_exhibitors_register(self, event, **searches):
        if not event.can_access_from_current_website():
            raise NotFound()

        return request.render(
            "website_event_exhibitors.event_exhibitors_register",
            self._event_exhibitors_get_values(event, **searches)
        )

    def _event_exhibitors_get_values(self, event, **searches):
        StandTypes = request.env['event.stand.type'].sudo().search([])
        visitor_sudo = request.env['website.visitor']._get_visitor_from_request()

        # return rendering values
        return {
            # event information
            'event': event,
            'main_object': event,
            "name": visitor_sudo.partner_id.name or None,
            "email": visitor_sudo.partner_id.email or None,
            "mobile": visitor_sudo.partner_id.mobile or None,
            "phone": visitor_sudo.partner_id.phone or None,
            "partner_company": visitor_sudo.partner_id.parent_id and visitor_sudo.partner_id.parent_id.name or None,

            # environment
            'hostname': request.httprequest.host.split(':')[0],
            'user_event_manager': request.env.user.has_group('event.group_event_manager'),

            'stand_types': StandTypes
        }


    @http.route(['''/event/<model("event.event"):event>/exhibitor_registration/new'''], type='http', auth="public", methods=['POST'], website=True)
    def registration_confirm(self, event, **post):
        if not event.can_access_from_current_website():
            raise werkzeug.exceptions.NotFound()

        registrations = self._process_exhibitor_data_form(event, post)
        exhibitor_sudo = self._create_exhibitor_from_registration_post(event, registrations)

        return request.render("website_event_exhibitors.registration_complete",
            self._get_registration_confirm_values(event, exhibitor_sudo))



    def _process_exhibitor_data_form(self, event, form_details):
        """ Process data posted from the exhibitor details form.

        :param form_details: posted data from frontend registration form, like
            {'1-name': 'r', '1-email': 'r@r.com', '1-phone': '', '1-event_ticket_id': '1'}
        """
        allowed_fields = request.env['event.sponsor']._get_website_registration_allowed_fields()
        registration_fields = {key: v for key, v in request.env['event.sponsor']._fields.items() if key in allowed_fields}

        registrations = {}
        global_values = {}
        for key, value in form_details.items():
            counter, attr_name = key.split('-', 1)
            field_name = attr_name.split('-')[0]
            if field_name not in registration_fields:
                continue
            elif isinstance(registration_fields[field_name], (fields.Many2one, fields.Integer)):
                value = int(value) or False  # 0 is considered as a void many2one aka False
            else:
                value = value

            if counter == '0':
                global_values[attr_name] = value
            else:
                registrations.setdefault(counter, dict())[attr_name] = value
        for key, value in global_values.items():
            for registration in registrations.values():
                registration[key] = value

        return list(registrations.values())

    def _create_exhibitor_from_registration_post(self, event, registration_data):
        """ Also try to set a visitor (from request) and
        a partner (if visitor linked to a user for example). Purpose is to gather
        as much informations as possible, notably to ease future communications.
        Also try to update visitor informations based on registration info. """
        visitor_sudo = request.env['website.visitor']._get_visitor_from_request(force_create=True)
        visitor_sudo._update_visitor_last_visit()
        visitor_values = {}
        registrations_to_create = []
        lead_vals = {}

        for registration_values in registration_data:
            registration_values['event_id'] = event.id

            if visitor_sudo.partner_id:
                registration_values['partner_id'] = visitor_sudo.partner_id.id
                lead_vals['partner_id'] = visitor_sudo.partner_id.id
            else:
                registration_values['partner_id'] = request.env.user.partner_id.id

            if visitor_sudo:
                # registration may give a name to the visitor, yay
                if registration_values.get('name') and not visitor_sudo.name and not visitor_values.get('name'):
                    visitor_values['name'] = registration_values['name']
                # update registration based on visitor
                registration_values['visitor_id'] = visitor_sudo.id

            registration_values['sponsor_type_id'] = 1  # FIXME: Remove this
            registrations_to_create.append(registration_values)

        if visitor_values:
            visitor_sudo.write(visitor_values)

        return request.env['event.sponsor'].sudo().create(registrations_to_create)


    def _get_registration_confirm_values(self, event, exhibitor_sudo):
        urls = event._get_event_resource_urls()
        return {
            'attendees': exhibitor_sudo,
            'event': event,
            'google_url': urls.get('google_url'),
            'iCal_url': urls.get('iCal_url')
        }
