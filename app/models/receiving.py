# encoding: utf-8
from decimal import Decimal

from app.app_provider import AppInfo
from app import const
from app.models.util import format_decimal
from app.models.enum_values import EnumValues
from sqlalchemy import Column, Integer, ForeignKey, Numeric, Text, DateTime, select, func
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import backref, relationship

db = AppInfo.get_db()


class Receiving(db.Model):
    __tablename__ = 'receiving'
    id = Column(Integer, primary_key=True)
    date = Column(DateTime, nullable=False)
    remark = Column(Text)

    status_id = Column(Integer, ForeignKey('enum_values.id'), nullable=False)
    status = relationship('EnumValues', foreign_keys=[status_id])

    purchase_order_id = Column(Integer, ForeignKey('purchase_order.id'), nullable=False)
    purchase_order = relationship('PurchaseOrder', backref=backref('po_receivings', uselist=True,))

    inventory_transaction_id = Column(Integer, ForeignKey('inventory_transaction.id'), nullable=True)
    inventory_transaction = relationship('InventoryTransaction',
                                         backref=backref('it_receiving', uselist=False, cascade='all, delete-orphan'))

    @staticmethod
    def status_filter():
        return EnumValues.type_filter('RECEIVING_STATUS')

    @hybrid_property
    def transient_po(self):
        """
        This design is to display a readonly field containing current
        Purchase order information in UI but don't allow user to change it.
        :return: Current purchase order instance as a transient property
        """
        return self.purchase_order

    @transient_po.setter
    def transient_po(self, val):
        pass

    @hybrid_property
    def supplier(self):
        return self.purchase_order.supplier

    @supplier.setter
    def supplier(self, val):
        pass

    @hybrid_property
    def total_amount(self):
        return format_decimal(Decimal(sum(line.total_amount for line in self.lines)))

    @total_amount.expression
    def total_amount(self):
        return (select([func.sum(ReceivingLine.price * ReceivingLine.quantity)])
                .where(self.id == ReceivingLine.receiving_id).label('total_amount'))

    @total_amount.setter
    def total_amount(self, value):
        pass

    @staticmethod
    def filter_by_po_id(po_id):
        return AppInfo.get_db().session.query(Receiving).filter_by(purchase_order_id=po_id).all()

    def __unicode__(self):
        return str(self.id) + ' - ' + str(self.total_amount)

    @staticmethod
    def create_draft_recv_from_po(po):
        recv_draft_status = EnumValues.find_one_by_code(const.RECEIVING_DRAFT_STATUS_KEY)
        purchase_in_trans_type = EnumValues.find_one_by_code(const.PURCHASE_IN_INV_TRANS_KEY)
        recv = Receiving()
        recv.purchase_order = po
        recv.purchase_order_id = po.id
        recv.date = po.order_date
        recv.status = recv_draft_status
        recv.supplier = po.supplier
        from app.models import InventoryTransaction
        trans = InventoryTransaction()
        trans.date = recv.date
        trans.type = purchase_in_trans_type
        recv.inventory_transaction = trans
        for line in po.lines:
            recv_l = ReceivingLine()
            recv_l.receiving = recv
            recv_l.price = line.unit_price
            recv_l.product = line.product
            recv_l.quantity = line.quantity
            recv_l.purchase_order_line = line
            from app.models import InventoryTransactionLine
            trans_l = InventoryTransactionLine()
            trans_l.price = recv_l.price
            trans_l.in_transit_quantity = recv_l.quantity
            trans_l.product = recv_l.product
            trans_l.quantity = 0
            trans_l.inventory_transaction = trans
            recv_l.inventory_transaction_line = trans_l
        return recv


class ReceivingLine(db.Model):
    __tablename = 'receiving_line'
    id = Column(Integer, primary_key=True)
    quantity = Column(Numeric(precision=8, scale=2, decimal_return_scale=2), nullable=False)
    price = Column(Numeric(precision=8, scale=2, decimal_return_scale=2), nullable=False)

    product_id = Column(Integer, ForeignKey('product.id'), nullable=False)
    product = relationship('Product', backref=backref('receiving_lines'))

    receiving_id = Column(Integer, ForeignKey('receiving.id'), nullable=False)
    receiving = relationship('Receiving', backref=backref('lines', uselist=True, cascade='all, delete-orphan'))

    purchase_order_line_id = Column(Integer, ForeignKey('purchase_order_line.id'), nullable=False)
    purchase_order_line = relationship('PurchaseOrderLine', backref=backref('pol_receiving_lines', uselist=True))

    inventory_transaction_line_id = Column(Integer, ForeignKey('inventory_transaction_line.id'), nullable=True)
    inventory_transaction_line = relationship('InventoryTransactionLine',
                                              backref=backref('itl_receiving_line', uselist=False,
                                                              cascade='all, delete-orphan'))

    @hybrid_property
    def total_amount(self):
        if self.quantity is None:
            q = 0
        else:
            q = self.quantity
        return format_decimal(Decimal(self.price * q))

    @total_amount.expression
    def total_amount(self):
        return select([self.price * self.quantity]).label('line_total_amount')

    @total_amount.setter
    def total_amount(self, value):
        pass

    @hybrid_property
    def transient_product(self):
        return self.product

    @transient_product.setter
    def transient_product(self, val):
        pass

    @hybrid_property
    def transient_price(self):
        return self.price

    @transient_price.setter
    def transient_price(self, val):
        pass
