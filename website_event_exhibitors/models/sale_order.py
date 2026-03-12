# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, api, _
from lxml import etree
import logging
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.depends('order_line.price_subtotal', 'order_line.discount', 'partner_id')
    def _event_amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        event_sale_type = self.env.ref('website_event_exhibitors.event_sale_type', False)

        if not event_sale_type:
            return

        Event_SOT = event_sale_type.id

        for order in self:
            if (order.type_id and order.type_id.id != Event_SOT):
                order.update({
                    'event_max_discount': 0,
                })
            else:
                amount_untaxed = amount_tax = max_cdiscount = 0.0
                cdiscount = []
                for line in order.order_line:
                    line_subtotal = line.price_subtotal if (int(line.price_subtotal - line.price_subtotal_disc_amt)) else line.price_subtotal_disc_amt
                    amount_untaxed += line_subtotal
                    cdiscount.append(line.discount)
                    if order.company_id.tax_calculation_rounding_method == 'round_globally':
                        price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
                        taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty,
                                                        product=line.product_id, partner=order.partner_id)
                        amount_tax += sum(t.get('amount', 0.0) for t in taxes.get('taxes', []))
                    else:
                        amount_tax += line.price_tax

                if cdiscount:
                    max_cdiscount = max(cdiscount)
                if order.pricelist_id.currency_id:
                    order.update({
                        'amount_untaxed': order.pricelist_id.currency_id.round(
                            amount_untaxed),
                        'amount_tax': order.pricelist_id.currency_id.round(amount_tax),
                        'amount_total': amount_untaxed + amount_tax,
                    })

                order.update({
                    'event_max_discount': max_cdiscount,
                })


    event_id = fields.Many2one('event.event', string='Event', ondelete='restrict', tracking=True)
    state = fields.Selection(selection_add=[
        ('submitted', "Submit for Approval"),
        ('approved1', "Approved by Sales Mgr"),
    ])
    event_max_discount = fields.Integer(compute='_event_amount_all', store=True, string="Event Maximum Discount")


    @api.onchange('brand_id')
    def _onchange_brand(self):
        Event_SOT = self.env.ref('website_event_exhibitors.event_sale_type').id

        # Event Orders:
        if (self.type_id and self.type_id.id != Event_SOT):
            return

        if self.brand_id:
            # If Event exists
            if self.event_id and self.event_id.brand_id.id != self.brand_id.id:
                self.event_id = False


    @api.onchange('event_id')
    def _onchange_event(self):
        Event_SOT = self.env.ref('website_event_exhibitors.event_sale_type').id

        # Event Orders:
        if (self.type_id and self.type_id.id != Event_SOT):
            return

        if self.event_id:
            self.website_id = self.event_id.website_id.id or False
            self.analytic_account_id = self.event_id.analytic_account_id.id or False

            line_ids = []
            for product in self.event_id.default_product_ids:
                line_ids += [
                    (
                        0,
                        0,
                        {
                            "product_id": product.id,
                            "product_uom_qty":1,
                        },
                    )]
            self.order_line = line_ids
            for line in self.order_line:
                line.product_id_change()

    def action_submit(self):
        orders = self.filtered(lambda s: s.state in ['draft'])
        for o in orders:
            if not o.order_line:
                raise UserError(_('You cannot submit a quotation/sales order which has no line.'))
        self.write({'state':'submitted'})
        
    def action_approve1(self):
        orders = self.filtered(lambda s: s.state in ['submitted'])
        orders.write({'state':'approved1'})
    
    def action_refuse(self):
        orders = self.filtered(lambda s: s.state in ['submitted', 'sale', 'sent', 'approved1'])
        orders.write({'state': 'draft'})
        return True

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        if self.event_id:
            default['analytic_account_id'] = self.event_id.analytic_account_id and self.event_id.analytic_account_id.id or False
        return super(SaleOrder, self).copy(default=default)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id', 'price_subtotal_disc_amt')
    @api.depends( 'discount', 'price_unit', 'tax_id', 'price_subtotal_disc_amt')
    def _compute_amount(self):
        """
        Compute the amounts of the SO line.
        """
        ctx = self.env.context
        EOT = self.env.ref('website_event_exhibitors.event_sale_type').id
        super(SaleOrderLine, self)._compute_amount()

        for line in self.filtered(lambda record: record.order_id.type_id.id == EOT):

            # price = round(line.price_unit * (1 - (line.discount or 0.0) / 100.0), 5)
            #
            # taxes = line.tax_id.compute_all(price, line.order_id.currency_id, 1,
            #                                 product=line.product_id, partner=line.order_id.partner_shipping_id)
            # price_subtotal = taxes['total_excluded']
            #
            # # if line.price_subtotal_disc_amt:
            # if 'price_subtotal_disc_amt_update' in ctx:
            #     line.discount = round((1.0 - float(line.price_subtotal_disc_amt) / (
            #                 float(price_subtotal) * float(line.product_uom_qty) or 1)) * 100.0, 5)
            # else:
            #     line.price_subtotal_disc_amt = price_subtotal

            if not line.discount:
                line.actual_unit_price = line.price_unit
                line.price_subtotal_disc_amt = line.price_subtotal
            else:
                line.actual_unit_price = float(line.price_subtotal_disc_amt) / (float(line.product_uom_qty) or 1)

    @api.depends('product_id', 'price_subtotal')
    def _compute_event_price_edit(self):
        EOT = self.env.ref('website_event_exhibitors.event_sale_type').id
        for line in self:
            if line.order_id.type_id.id != EOT:
                continue

            sub_dis_amt = line.price_subtotal_disc_amt
            subtotal = line.price_subtotal
            event_price_edit = False
            if line.order_id.type_id.id == EOT:
                line.event_price_edit = False
                if line.product_template_id and line.product_template_id.price_edit:
                    event_price_edit = True
            line.update({
                'event_price_edit': event_price_edit,
            })
            if not sub_dis_amt:
                line.update({
                    'price_subtotal_disc_amt': subtotal
                })

            # price = round(line.price_unit * (1 - (line.discount or 0.0) / 100.0), 5)
            price = line.actual_unit_price

            taxes = line.tax_id.compute_all(
                price,
                line.order_id.currency_id,
                line.product_uom_qty,
                product=line.product_id,
                partner=line.order_id.partner_id
            )

            line.update({
                'price_tax': taxes['total_included'] - taxes['total_excluded'],
                'price_total': taxes['total_included'],
                'price_subtotal': taxes['total_excluded'],
            })

            if int(subtotal - sub_dis_amt) == 0:
                line.update({
                    'price_subtotal': sub_dis_amt
                })

    price_subtotal_disc_amt = fields.Monetary(string='Subtotal after discount', copy=False)
    event_price_edit = fields.Boolean(compute='_compute_event_price_edit', string='Event Price Editable', store=True)
    actual_unit_price = fields.Float(compute='_compute_amount', string='Actual Unit Price', digits='Product Price',
                                     default=0.0, readonly=True, store=True)

    @api.onchange('price_subtotal_disc_amt', 'product_uom_qty', 'price_unit', 'discount')
    def _onchange_subtotal_discount(self):
        ctx = self.env.context
        Event_SOT = self.env.ref('website_event_exhibitors.event_sale_type').id
        if self.order_id.type_id.id == Event_SOT:
            if 'price_subtotal_disc_amt_update' in ctx:
                taxes = self.tax_id.compute_all(self.price_unit, self.order_id.currency_id, 1,
                                                product=self.product_id, partner=self.order_id.partner_shipping_id)
                price_subtotal = taxes['total_excluded']

                self.discount = round((1.0 - float(self.price_subtotal_disc_amt) / (
                            float(price_subtotal) * float(self.product_uom_qty))) * 100.0, 5)

            else: # Reset
                self.price_subtotal_disc_amt = self.price_subtotal

    @api.onchange('product_id')
    def reset_discount_price_subtotal_disc_amt(self):
        Event_SOT = self.env.ref('website_event_exhibitors.event_sale_type').id
        if self.order_id.type_id.id == Event_SOT:
            self.discount = 0
            self.price_subtotal_disc_amt = 0

    def _prepare_invoice_line(self, **optional_values):
        values = super()._prepare_invoice_line(**optional_values)
        Event_SOT = self.env.ref('website_event_exhibitors.event_sale_type').id

        if self.order_id.type_id.id == Event_SOT:
            values['discount'] = 0 # Nullify Disc %
            values['price_unit'] = self.actual_unit_price
            values['lock_prices'] = True
      
        if self.order_id.event_id:
            event = self.order_id.event_id
            event = event.with_context(tz=event.date_tz)
            if 'from_date' in self.env['account.move.line']._fields:
                values['from_date'] = fields.Datetime.context_timestamp(
                    event, event.date_begin,
                ).date()
            if 'to_date' in self.env['account.move.line']._fields:
                values['to_date'] = fields.Datetime.context_timestamp(
                    event, event.date_end,
                ).date()
        return values
