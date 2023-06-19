# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
import logging

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    event_id = fields.Many2one('event.event', string='Event')
    event_attr_value_id = fields.Many2one('product.attribute.value', related='event_id.attribute_value_id', store=True)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.model
    def _get_domain4event_products(self):
        # FIXME
        # If Event/Attribute not found, set default domain
        # return "[('sale_ok', '=', True), '|', ('company_id', '=', False), ('company_id', '=', parent.company_id), ('id', 'in', parent.event_product_ids)]"

        return "[('sale_ok', '=', True), '|', ('company_id', '=', False), ('company_id', '=', parent.company_id), " \
               "('product_template_attribute_value_ids.product_attribute_value_id', '=', parent.event_attr_value_id)]"


    # Inherited
    product_id = fields.Many2one('product.product', domain=_get_domain4event_products)


