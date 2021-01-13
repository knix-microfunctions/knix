/**
 * Autogenerated by Thrift Compiler (0.13.0)
 *
 * DO NOT EDIT UNLESS YOU ARE SURE THAT YOU KNOW WHAT YOU ARE DOING
 *  @generated
 */
package org.microfunctions.mfnapi;

@SuppressWarnings({"cast", "rawtypes", "serial", "unchecked", "unused"})
@javax.annotation.Generated(value = "Autogenerated by Thrift Compiler (0.13.0)", date = "2021-01-13")
public class TriggerInfoAMQP implements org.apache.thrift.TBase<TriggerInfoAMQP, TriggerInfoAMQP._Fields>, java.io.Serializable, Cloneable, Comparable<TriggerInfoAMQP> {
  private static final org.apache.thrift.protocol.TStruct STRUCT_DESC = new org.apache.thrift.protocol.TStruct("TriggerInfoAMQP");

  private static final org.apache.thrift.protocol.TField AMQP_ADDR_FIELD_DESC = new org.apache.thrift.protocol.TField("amqp_addr", org.apache.thrift.protocol.TType.STRING, (short)1);
  private static final org.apache.thrift.protocol.TField ROUTING_KEY_FIELD_DESC = new org.apache.thrift.protocol.TField("routing_key", org.apache.thrift.protocol.TType.STRING, (short)2);
  private static final org.apache.thrift.protocol.TField EXCHANGE_FIELD_DESC = new org.apache.thrift.protocol.TField("exchange", org.apache.thrift.protocol.TType.STRING, (short)3);
  private static final org.apache.thrift.protocol.TField WITH_ACK_FIELD_DESC = new org.apache.thrift.protocol.TField("with_ack", org.apache.thrift.protocol.TType.BOOL, (short)4);
  private static final org.apache.thrift.protocol.TField DURABLE_FIELD_DESC = new org.apache.thrift.protocol.TField("durable", org.apache.thrift.protocol.TType.BOOL, (short)5);
  private static final org.apache.thrift.protocol.TField EXCLUSIVE_FIELD_DESC = new org.apache.thrift.protocol.TField("exclusive", org.apache.thrift.protocol.TType.BOOL, (short)6);
  private static final org.apache.thrift.protocol.TField IGNR_MSG_PROB_FIELD_DESC = new org.apache.thrift.protocol.TField("ignr_msg_prob", org.apache.thrift.protocol.TType.DOUBLE, (short)7);

  private static final org.apache.thrift.scheme.SchemeFactory STANDARD_SCHEME_FACTORY = new TriggerInfoAMQPStandardSchemeFactory();
  private static final org.apache.thrift.scheme.SchemeFactory TUPLE_SCHEME_FACTORY = new TriggerInfoAMQPTupleSchemeFactory();

  public @org.apache.thrift.annotation.Nullable java.lang.String amqp_addr; // required
  public @org.apache.thrift.annotation.Nullable java.lang.String routing_key; // required
  public @org.apache.thrift.annotation.Nullable java.lang.String exchange; // required
  public boolean with_ack; // required
  public boolean durable; // required
  public boolean exclusive; // required
  public double ignr_msg_prob; // required

  /** The set of fields this struct contains, along with convenience methods for finding and manipulating them. */
  public enum _Fields implements org.apache.thrift.TFieldIdEnum {
    AMQP_ADDR((short)1, "amqp_addr"),
    ROUTING_KEY((short)2, "routing_key"),
    EXCHANGE((short)3, "exchange"),
    WITH_ACK((short)4, "with_ack"),
    DURABLE((short)5, "durable"),
    EXCLUSIVE((short)6, "exclusive"),
    IGNR_MSG_PROB((short)7, "ignr_msg_prob");

    private static final java.util.Map<java.lang.String, _Fields> byName = new java.util.HashMap<java.lang.String, _Fields>();

    static {
      for (_Fields field : java.util.EnumSet.allOf(_Fields.class)) {
        byName.put(field.getFieldName(), field);
      }
    }

    /**
     * Find the _Fields constant that matches fieldId, or null if its not found.
     */
    @org.apache.thrift.annotation.Nullable
    public static _Fields findByThriftId(int fieldId) {
      switch(fieldId) {
        case 1: // AMQP_ADDR
          return AMQP_ADDR;
        case 2: // ROUTING_KEY
          return ROUTING_KEY;
        case 3: // EXCHANGE
          return EXCHANGE;
        case 4: // WITH_ACK
          return WITH_ACK;
        case 5: // DURABLE
          return DURABLE;
        case 6: // EXCLUSIVE
          return EXCLUSIVE;
        case 7: // IGNR_MSG_PROB
          return IGNR_MSG_PROB;
        default:
          return null;
      }
    }

    /**
     * Find the _Fields constant that matches fieldId, throwing an exception
     * if it is not found.
     */
    public static _Fields findByThriftIdOrThrow(int fieldId) {
      _Fields fields = findByThriftId(fieldId);
      if (fields == null) throw new java.lang.IllegalArgumentException("Field " + fieldId + " doesn't exist!");
      return fields;
    }

    /**
     * Find the _Fields constant that matches name, or null if its not found.
     */
    @org.apache.thrift.annotation.Nullable
    public static _Fields findByName(java.lang.String name) {
      return byName.get(name);
    }

    private final short _thriftId;
    private final java.lang.String _fieldName;

    _Fields(short thriftId, java.lang.String fieldName) {
      _thriftId = thriftId;
      _fieldName = fieldName;
    }

    public short getThriftFieldId() {
      return _thriftId;
    }

    public java.lang.String getFieldName() {
      return _fieldName;
    }
  }

  // isset id assignments
  private static final int __WITH_ACK_ISSET_ID = 0;
  private static final int __DURABLE_ISSET_ID = 1;
  private static final int __EXCLUSIVE_ISSET_ID = 2;
  private static final int __IGNR_MSG_PROB_ISSET_ID = 3;
  private byte __isset_bitfield = 0;
  public static final java.util.Map<_Fields, org.apache.thrift.meta_data.FieldMetaData> metaDataMap;
  static {
    java.util.Map<_Fields, org.apache.thrift.meta_data.FieldMetaData> tmpMap = new java.util.EnumMap<_Fields, org.apache.thrift.meta_data.FieldMetaData>(_Fields.class);
    tmpMap.put(_Fields.AMQP_ADDR, new org.apache.thrift.meta_data.FieldMetaData("amqp_addr", org.apache.thrift.TFieldRequirementType.DEFAULT, 
        new org.apache.thrift.meta_data.FieldValueMetaData(org.apache.thrift.protocol.TType.STRING)));
    tmpMap.put(_Fields.ROUTING_KEY, new org.apache.thrift.meta_data.FieldMetaData("routing_key", org.apache.thrift.TFieldRequirementType.DEFAULT, 
        new org.apache.thrift.meta_data.FieldValueMetaData(org.apache.thrift.protocol.TType.STRING)));
    tmpMap.put(_Fields.EXCHANGE, new org.apache.thrift.meta_data.FieldMetaData("exchange", org.apache.thrift.TFieldRequirementType.DEFAULT, 
        new org.apache.thrift.meta_data.FieldValueMetaData(org.apache.thrift.protocol.TType.STRING)));
    tmpMap.put(_Fields.WITH_ACK, new org.apache.thrift.meta_data.FieldMetaData("with_ack", org.apache.thrift.TFieldRequirementType.DEFAULT, 
        new org.apache.thrift.meta_data.FieldValueMetaData(org.apache.thrift.protocol.TType.BOOL)));
    tmpMap.put(_Fields.DURABLE, new org.apache.thrift.meta_data.FieldMetaData("durable", org.apache.thrift.TFieldRequirementType.DEFAULT, 
        new org.apache.thrift.meta_data.FieldValueMetaData(org.apache.thrift.protocol.TType.BOOL)));
    tmpMap.put(_Fields.EXCLUSIVE, new org.apache.thrift.meta_data.FieldMetaData("exclusive", org.apache.thrift.TFieldRequirementType.DEFAULT, 
        new org.apache.thrift.meta_data.FieldValueMetaData(org.apache.thrift.protocol.TType.BOOL)));
    tmpMap.put(_Fields.IGNR_MSG_PROB, new org.apache.thrift.meta_data.FieldMetaData("ignr_msg_prob", org.apache.thrift.TFieldRequirementType.DEFAULT, 
        new org.apache.thrift.meta_data.FieldValueMetaData(org.apache.thrift.protocol.TType.DOUBLE)));
    metaDataMap = java.util.Collections.unmodifiableMap(tmpMap);
    org.apache.thrift.meta_data.FieldMetaData.addStructMetaDataMap(TriggerInfoAMQP.class, metaDataMap);
  }

  public TriggerInfoAMQP() {
  }

  public TriggerInfoAMQP(
    java.lang.String amqp_addr,
    java.lang.String routing_key,
    java.lang.String exchange,
    boolean with_ack,
    boolean durable,
    boolean exclusive,
    double ignr_msg_prob)
  {
    this();
    this.amqp_addr = amqp_addr;
    this.routing_key = routing_key;
    this.exchange = exchange;
    this.with_ack = with_ack;
    setWith_ackIsSet(true);
    this.durable = durable;
    setDurableIsSet(true);
    this.exclusive = exclusive;
    setExclusiveIsSet(true);
    this.ignr_msg_prob = ignr_msg_prob;
    setIgnr_msg_probIsSet(true);
  }

  /**
   * Performs a deep copy on <i>other</i>.
   */
  public TriggerInfoAMQP(TriggerInfoAMQP other) {
    __isset_bitfield = other.__isset_bitfield;
    if (other.isSetAmqp_addr()) {
      this.amqp_addr = other.amqp_addr;
    }
    if (other.isSetRouting_key()) {
      this.routing_key = other.routing_key;
    }
    if (other.isSetExchange()) {
      this.exchange = other.exchange;
    }
    this.with_ack = other.with_ack;
    this.durable = other.durable;
    this.exclusive = other.exclusive;
    this.ignr_msg_prob = other.ignr_msg_prob;
  }

  public TriggerInfoAMQP deepCopy() {
    return new TriggerInfoAMQP(this);
  }

  @Override
  public void clear() {
    this.amqp_addr = null;
    this.routing_key = null;
    this.exchange = null;
    setWith_ackIsSet(false);
    this.with_ack = false;
    setDurableIsSet(false);
    this.durable = false;
    setExclusiveIsSet(false);
    this.exclusive = false;
    setIgnr_msg_probIsSet(false);
    this.ignr_msg_prob = 0.0;
  }

  @org.apache.thrift.annotation.Nullable
  public java.lang.String getAmqp_addr() {
    return this.amqp_addr;
  }

  public TriggerInfoAMQP setAmqp_addr(@org.apache.thrift.annotation.Nullable java.lang.String amqp_addr) {
    this.amqp_addr = amqp_addr;
    return this;
  }

  public void unsetAmqp_addr() {
    this.amqp_addr = null;
  }

  /** Returns true if field amqp_addr is set (has been assigned a value) and false otherwise */
  public boolean isSetAmqp_addr() {
    return this.amqp_addr != null;
  }

  public void setAmqp_addrIsSet(boolean value) {
    if (!value) {
      this.amqp_addr = null;
    }
  }

  @org.apache.thrift.annotation.Nullable
  public java.lang.String getRouting_key() {
    return this.routing_key;
  }

  public TriggerInfoAMQP setRouting_key(@org.apache.thrift.annotation.Nullable java.lang.String routing_key) {
    this.routing_key = routing_key;
    return this;
  }

  public void unsetRouting_key() {
    this.routing_key = null;
  }

  /** Returns true if field routing_key is set (has been assigned a value) and false otherwise */
  public boolean isSetRouting_key() {
    return this.routing_key != null;
  }

  public void setRouting_keyIsSet(boolean value) {
    if (!value) {
      this.routing_key = null;
    }
  }

  @org.apache.thrift.annotation.Nullable
  public java.lang.String getExchange() {
    return this.exchange;
  }

  public TriggerInfoAMQP setExchange(@org.apache.thrift.annotation.Nullable java.lang.String exchange) {
    this.exchange = exchange;
    return this;
  }

  public void unsetExchange() {
    this.exchange = null;
  }

  /** Returns true if field exchange is set (has been assigned a value) and false otherwise */
  public boolean isSetExchange() {
    return this.exchange != null;
  }

  public void setExchangeIsSet(boolean value) {
    if (!value) {
      this.exchange = null;
    }
  }

  public boolean isWith_ack() {
    return this.with_ack;
  }

  public TriggerInfoAMQP setWith_ack(boolean with_ack) {
    this.with_ack = with_ack;
    setWith_ackIsSet(true);
    return this;
  }

  public void unsetWith_ack() {
    __isset_bitfield = org.apache.thrift.EncodingUtils.clearBit(__isset_bitfield, __WITH_ACK_ISSET_ID);
  }

  /** Returns true if field with_ack is set (has been assigned a value) and false otherwise */
  public boolean isSetWith_ack() {
    return org.apache.thrift.EncodingUtils.testBit(__isset_bitfield, __WITH_ACK_ISSET_ID);
  }

  public void setWith_ackIsSet(boolean value) {
    __isset_bitfield = org.apache.thrift.EncodingUtils.setBit(__isset_bitfield, __WITH_ACK_ISSET_ID, value);
  }

  public boolean isDurable() {
    return this.durable;
  }

  public TriggerInfoAMQP setDurable(boolean durable) {
    this.durable = durable;
    setDurableIsSet(true);
    return this;
  }

  public void unsetDurable() {
    __isset_bitfield = org.apache.thrift.EncodingUtils.clearBit(__isset_bitfield, __DURABLE_ISSET_ID);
  }

  /** Returns true if field durable is set (has been assigned a value) and false otherwise */
  public boolean isSetDurable() {
    return org.apache.thrift.EncodingUtils.testBit(__isset_bitfield, __DURABLE_ISSET_ID);
  }

  public void setDurableIsSet(boolean value) {
    __isset_bitfield = org.apache.thrift.EncodingUtils.setBit(__isset_bitfield, __DURABLE_ISSET_ID, value);
  }

  public boolean isExclusive() {
    return this.exclusive;
  }

  public TriggerInfoAMQP setExclusive(boolean exclusive) {
    this.exclusive = exclusive;
    setExclusiveIsSet(true);
    return this;
  }

  public void unsetExclusive() {
    __isset_bitfield = org.apache.thrift.EncodingUtils.clearBit(__isset_bitfield, __EXCLUSIVE_ISSET_ID);
  }

  /** Returns true if field exclusive is set (has been assigned a value) and false otherwise */
  public boolean isSetExclusive() {
    return org.apache.thrift.EncodingUtils.testBit(__isset_bitfield, __EXCLUSIVE_ISSET_ID);
  }

  public void setExclusiveIsSet(boolean value) {
    __isset_bitfield = org.apache.thrift.EncodingUtils.setBit(__isset_bitfield, __EXCLUSIVE_ISSET_ID, value);
  }

  public double getIgnr_msg_prob() {
    return this.ignr_msg_prob;
  }

  public TriggerInfoAMQP setIgnr_msg_prob(double ignr_msg_prob) {
    this.ignr_msg_prob = ignr_msg_prob;
    setIgnr_msg_probIsSet(true);
    return this;
  }

  public void unsetIgnr_msg_prob() {
    __isset_bitfield = org.apache.thrift.EncodingUtils.clearBit(__isset_bitfield, __IGNR_MSG_PROB_ISSET_ID);
  }

  /** Returns true if field ignr_msg_prob is set (has been assigned a value) and false otherwise */
  public boolean isSetIgnr_msg_prob() {
    return org.apache.thrift.EncodingUtils.testBit(__isset_bitfield, __IGNR_MSG_PROB_ISSET_ID);
  }

  public void setIgnr_msg_probIsSet(boolean value) {
    __isset_bitfield = org.apache.thrift.EncodingUtils.setBit(__isset_bitfield, __IGNR_MSG_PROB_ISSET_ID, value);
  }

  public void setFieldValue(_Fields field, @org.apache.thrift.annotation.Nullable java.lang.Object value) {
    switch (field) {
    case AMQP_ADDR:
      if (value == null) {
        unsetAmqp_addr();
      } else {
        setAmqp_addr((java.lang.String)value);
      }
      break;

    case ROUTING_KEY:
      if (value == null) {
        unsetRouting_key();
      } else {
        setRouting_key((java.lang.String)value);
      }
      break;

    case EXCHANGE:
      if (value == null) {
        unsetExchange();
      } else {
        setExchange((java.lang.String)value);
      }
      break;

    case WITH_ACK:
      if (value == null) {
        unsetWith_ack();
      } else {
        setWith_ack((java.lang.Boolean)value);
      }
      break;

    case DURABLE:
      if (value == null) {
        unsetDurable();
      } else {
        setDurable((java.lang.Boolean)value);
      }
      break;

    case EXCLUSIVE:
      if (value == null) {
        unsetExclusive();
      } else {
        setExclusive((java.lang.Boolean)value);
      }
      break;

    case IGNR_MSG_PROB:
      if (value == null) {
        unsetIgnr_msg_prob();
      } else {
        setIgnr_msg_prob((java.lang.Double)value);
      }
      break;

    }
  }

  @org.apache.thrift.annotation.Nullable
  public java.lang.Object getFieldValue(_Fields field) {
    switch (field) {
    case AMQP_ADDR:
      return getAmqp_addr();

    case ROUTING_KEY:
      return getRouting_key();

    case EXCHANGE:
      return getExchange();

    case WITH_ACK:
      return isWith_ack();

    case DURABLE:
      return isDurable();

    case EXCLUSIVE:
      return isExclusive();

    case IGNR_MSG_PROB:
      return getIgnr_msg_prob();

    }
    throw new java.lang.IllegalStateException();
  }

  /** Returns true if field corresponding to fieldID is set (has been assigned a value) and false otherwise */
  public boolean isSet(_Fields field) {
    if (field == null) {
      throw new java.lang.IllegalArgumentException();
    }

    switch (field) {
    case AMQP_ADDR:
      return isSetAmqp_addr();
    case ROUTING_KEY:
      return isSetRouting_key();
    case EXCHANGE:
      return isSetExchange();
    case WITH_ACK:
      return isSetWith_ack();
    case DURABLE:
      return isSetDurable();
    case EXCLUSIVE:
      return isSetExclusive();
    case IGNR_MSG_PROB:
      return isSetIgnr_msg_prob();
    }
    throw new java.lang.IllegalStateException();
  }

  @Override
  public boolean equals(java.lang.Object that) {
    if (that == null)
      return false;
    if (that instanceof TriggerInfoAMQP)
      return this.equals((TriggerInfoAMQP)that);
    return false;
  }

  public boolean equals(TriggerInfoAMQP that) {
    if (that == null)
      return false;
    if (this == that)
      return true;

    boolean this_present_amqp_addr = true && this.isSetAmqp_addr();
    boolean that_present_amqp_addr = true && that.isSetAmqp_addr();
    if (this_present_amqp_addr || that_present_amqp_addr) {
      if (!(this_present_amqp_addr && that_present_amqp_addr))
        return false;
      if (!this.amqp_addr.equals(that.amqp_addr))
        return false;
    }

    boolean this_present_routing_key = true && this.isSetRouting_key();
    boolean that_present_routing_key = true && that.isSetRouting_key();
    if (this_present_routing_key || that_present_routing_key) {
      if (!(this_present_routing_key && that_present_routing_key))
        return false;
      if (!this.routing_key.equals(that.routing_key))
        return false;
    }

    boolean this_present_exchange = true && this.isSetExchange();
    boolean that_present_exchange = true && that.isSetExchange();
    if (this_present_exchange || that_present_exchange) {
      if (!(this_present_exchange && that_present_exchange))
        return false;
      if (!this.exchange.equals(that.exchange))
        return false;
    }

    boolean this_present_with_ack = true;
    boolean that_present_with_ack = true;
    if (this_present_with_ack || that_present_with_ack) {
      if (!(this_present_with_ack && that_present_with_ack))
        return false;
      if (this.with_ack != that.with_ack)
        return false;
    }

    boolean this_present_durable = true;
    boolean that_present_durable = true;
    if (this_present_durable || that_present_durable) {
      if (!(this_present_durable && that_present_durable))
        return false;
      if (this.durable != that.durable)
        return false;
    }

    boolean this_present_exclusive = true;
    boolean that_present_exclusive = true;
    if (this_present_exclusive || that_present_exclusive) {
      if (!(this_present_exclusive && that_present_exclusive))
        return false;
      if (this.exclusive != that.exclusive)
        return false;
    }

    boolean this_present_ignr_msg_prob = true;
    boolean that_present_ignr_msg_prob = true;
    if (this_present_ignr_msg_prob || that_present_ignr_msg_prob) {
      if (!(this_present_ignr_msg_prob && that_present_ignr_msg_prob))
        return false;
      if (this.ignr_msg_prob != that.ignr_msg_prob)
        return false;
    }

    return true;
  }

  @Override
  public int hashCode() {
    int hashCode = 1;

    hashCode = hashCode * 8191 + ((isSetAmqp_addr()) ? 131071 : 524287);
    if (isSetAmqp_addr())
      hashCode = hashCode * 8191 + amqp_addr.hashCode();

    hashCode = hashCode * 8191 + ((isSetRouting_key()) ? 131071 : 524287);
    if (isSetRouting_key())
      hashCode = hashCode * 8191 + routing_key.hashCode();

    hashCode = hashCode * 8191 + ((isSetExchange()) ? 131071 : 524287);
    if (isSetExchange())
      hashCode = hashCode * 8191 + exchange.hashCode();

    hashCode = hashCode * 8191 + ((with_ack) ? 131071 : 524287);

    hashCode = hashCode * 8191 + ((durable) ? 131071 : 524287);

    hashCode = hashCode * 8191 + ((exclusive) ? 131071 : 524287);

    hashCode = hashCode * 8191 + org.apache.thrift.TBaseHelper.hashCode(ignr_msg_prob);

    return hashCode;
  }

  @Override
  public int compareTo(TriggerInfoAMQP other) {
    if (!getClass().equals(other.getClass())) {
      return getClass().getName().compareTo(other.getClass().getName());
    }

    int lastComparison = 0;

    lastComparison = java.lang.Boolean.valueOf(isSetAmqp_addr()).compareTo(other.isSetAmqp_addr());
    if (lastComparison != 0) {
      return lastComparison;
    }
    if (isSetAmqp_addr()) {
      lastComparison = org.apache.thrift.TBaseHelper.compareTo(this.amqp_addr, other.amqp_addr);
      if (lastComparison != 0) {
        return lastComparison;
      }
    }
    lastComparison = java.lang.Boolean.valueOf(isSetRouting_key()).compareTo(other.isSetRouting_key());
    if (lastComparison != 0) {
      return lastComparison;
    }
    if (isSetRouting_key()) {
      lastComparison = org.apache.thrift.TBaseHelper.compareTo(this.routing_key, other.routing_key);
      if (lastComparison != 0) {
        return lastComparison;
      }
    }
    lastComparison = java.lang.Boolean.valueOf(isSetExchange()).compareTo(other.isSetExchange());
    if (lastComparison != 0) {
      return lastComparison;
    }
    if (isSetExchange()) {
      lastComparison = org.apache.thrift.TBaseHelper.compareTo(this.exchange, other.exchange);
      if (lastComparison != 0) {
        return lastComparison;
      }
    }
    lastComparison = java.lang.Boolean.valueOf(isSetWith_ack()).compareTo(other.isSetWith_ack());
    if (lastComparison != 0) {
      return lastComparison;
    }
    if (isSetWith_ack()) {
      lastComparison = org.apache.thrift.TBaseHelper.compareTo(this.with_ack, other.with_ack);
      if (lastComparison != 0) {
        return lastComparison;
      }
    }
    lastComparison = java.lang.Boolean.valueOf(isSetDurable()).compareTo(other.isSetDurable());
    if (lastComparison != 0) {
      return lastComparison;
    }
    if (isSetDurable()) {
      lastComparison = org.apache.thrift.TBaseHelper.compareTo(this.durable, other.durable);
      if (lastComparison != 0) {
        return lastComparison;
      }
    }
    lastComparison = java.lang.Boolean.valueOf(isSetExclusive()).compareTo(other.isSetExclusive());
    if (lastComparison != 0) {
      return lastComparison;
    }
    if (isSetExclusive()) {
      lastComparison = org.apache.thrift.TBaseHelper.compareTo(this.exclusive, other.exclusive);
      if (lastComparison != 0) {
        return lastComparison;
      }
    }
    lastComparison = java.lang.Boolean.valueOf(isSetIgnr_msg_prob()).compareTo(other.isSetIgnr_msg_prob());
    if (lastComparison != 0) {
      return lastComparison;
    }
    if (isSetIgnr_msg_prob()) {
      lastComparison = org.apache.thrift.TBaseHelper.compareTo(this.ignr_msg_prob, other.ignr_msg_prob);
      if (lastComparison != 0) {
        return lastComparison;
      }
    }
    return 0;
  }

  @org.apache.thrift.annotation.Nullable
  public _Fields fieldForId(int fieldId) {
    return _Fields.findByThriftId(fieldId);
  }

  public void read(org.apache.thrift.protocol.TProtocol iprot) throws org.apache.thrift.TException {
    scheme(iprot).read(iprot, this);
  }

  public void write(org.apache.thrift.protocol.TProtocol oprot) throws org.apache.thrift.TException {
    scheme(oprot).write(oprot, this);
  }

  @Override
  public java.lang.String toString() {
    java.lang.StringBuilder sb = new java.lang.StringBuilder("TriggerInfoAMQP(");
    boolean first = true;

    sb.append("amqp_addr:");
    if (this.amqp_addr == null) {
      sb.append("null");
    } else {
      sb.append(this.amqp_addr);
    }
    first = false;
    if (!first) sb.append(", ");
    sb.append("routing_key:");
    if (this.routing_key == null) {
      sb.append("null");
    } else {
      sb.append(this.routing_key);
    }
    first = false;
    if (!first) sb.append(", ");
    sb.append("exchange:");
    if (this.exchange == null) {
      sb.append("null");
    } else {
      sb.append(this.exchange);
    }
    first = false;
    if (!first) sb.append(", ");
    sb.append("with_ack:");
    sb.append(this.with_ack);
    first = false;
    if (!first) sb.append(", ");
    sb.append("durable:");
    sb.append(this.durable);
    first = false;
    if (!first) sb.append(", ");
    sb.append("exclusive:");
    sb.append(this.exclusive);
    first = false;
    if (!first) sb.append(", ");
    sb.append("ignr_msg_prob:");
    sb.append(this.ignr_msg_prob);
    first = false;
    sb.append(")");
    return sb.toString();
  }

  public void validate() throws org.apache.thrift.TException {
    // check for required fields
    // check for sub-struct validity
  }

  private void writeObject(java.io.ObjectOutputStream out) throws java.io.IOException {
    try {
      write(new org.apache.thrift.protocol.TCompactProtocol(new org.apache.thrift.transport.TIOStreamTransport(out)));
    } catch (org.apache.thrift.TException te) {
      throw new java.io.IOException(te);
    }
  }

  private void readObject(java.io.ObjectInputStream in) throws java.io.IOException, java.lang.ClassNotFoundException {
    try {
      // it doesn't seem like you should have to do this, but java serialization is wacky, and doesn't call the default constructor.
      __isset_bitfield = 0;
      read(new org.apache.thrift.protocol.TCompactProtocol(new org.apache.thrift.transport.TIOStreamTransport(in)));
    } catch (org.apache.thrift.TException te) {
      throw new java.io.IOException(te);
    }
  }

  private static class TriggerInfoAMQPStandardSchemeFactory implements org.apache.thrift.scheme.SchemeFactory {
    public TriggerInfoAMQPStandardScheme getScheme() {
      return new TriggerInfoAMQPStandardScheme();
    }
  }

  private static class TriggerInfoAMQPStandardScheme extends org.apache.thrift.scheme.StandardScheme<TriggerInfoAMQP> {

    public void read(org.apache.thrift.protocol.TProtocol iprot, TriggerInfoAMQP struct) throws org.apache.thrift.TException {
      org.apache.thrift.protocol.TField schemeField;
      iprot.readStructBegin();
      while (true)
      {
        schemeField = iprot.readFieldBegin();
        if (schemeField.type == org.apache.thrift.protocol.TType.STOP) { 
          break;
        }
        switch (schemeField.id) {
          case 1: // AMQP_ADDR
            if (schemeField.type == org.apache.thrift.protocol.TType.STRING) {
              struct.amqp_addr = iprot.readString();
              struct.setAmqp_addrIsSet(true);
            } else { 
              org.apache.thrift.protocol.TProtocolUtil.skip(iprot, schemeField.type);
            }
            break;
          case 2: // ROUTING_KEY
            if (schemeField.type == org.apache.thrift.protocol.TType.STRING) {
              struct.routing_key = iprot.readString();
              struct.setRouting_keyIsSet(true);
            } else { 
              org.apache.thrift.protocol.TProtocolUtil.skip(iprot, schemeField.type);
            }
            break;
          case 3: // EXCHANGE
            if (schemeField.type == org.apache.thrift.protocol.TType.STRING) {
              struct.exchange = iprot.readString();
              struct.setExchangeIsSet(true);
            } else { 
              org.apache.thrift.protocol.TProtocolUtil.skip(iprot, schemeField.type);
            }
            break;
          case 4: // WITH_ACK
            if (schemeField.type == org.apache.thrift.protocol.TType.BOOL) {
              struct.with_ack = iprot.readBool();
              struct.setWith_ackIsSet(true);
            } else { 
              org.apache.thrift.protocol.TProtocolUtil.skip(iprot, schemeField.type);
            }
            break;
          case 5: // DURABLE
            if (schemeField.type == org.apache.thrift.protocol.TType.BOOL) {
              struct.durable = iprot.readBool();
              struct.setDurableIsSet(true);
            } else { 
              org.apache.thrift.protocol.TProtocolUtil.skip(iprot, schemeField.type);
            }
            break;
          case 6: // EXCLUSIVE
            if (schemeField.type == org.apache.thrift.protocol.TType.BOOL) {
              struct.exclusive = iprot.readBool();
              struct.setExclusiveIsSet(true);
            } else { 
              org.apache.thrift.protocol.TProtocolUtil.skip(iprot, schemeField.type);
            }
            break;
          case 7: // IGNR_MSG_PROB
            if (schemeField.type == org.apache.thrift.protocol.TType.DOUBLE) {
              struct.ignr_msg_prob = iprot.readDouble();
              struct.setIgnr_msg_probIsSet(true);
            } else { 
              org.apache.thrift.protocol.TProtocolUtil.skip(iprot, schemeField.type);
            }
            break;
          default:
            org.apache.thrift.protocol.TProtocolUtil.skip(iprot, schemeField.type);
        }
        iprot.readFieldEnd();
      }
      iprot.readStructEnd();

      // check for required fields of primitive type, which can't be checked in the validate method
      struct.validate();
    }

    public void write(org.apache.thrift.protocol.TProtocol oprot, TriggerInfoAMQP struct) throws org.apache.thrift.TException {
      struct.validate();

      oprot.writeStructBegin(STRUCT_DESC);
      if (struct.amqp_addr != null) {
        oprot.writeFieldBegin(AMQP_ADDR_FIELD_DESC);
        oprot.writeString(struct.amqp_addr);
        oprot.writeFieldEnd();
      }
      if (struct.routing_key != null) {
        oprot.writeFieldBegin(ROUTING_KEY_FIELD_DESC);
        oprot.writeString(struct.routing_key);
        oprot.writeFieldEnd();
      }
      if (struct.exchange != null) {
        oprot.writeFieldBegin(EXCHANGE_FIELD_DESC);
        oprot.writeString(struct.exchange);
        oprot.writeFieldEnd();
      }
      oprot.writeFieldBegin(WITH_ACK_FIELD_DESC);
      oprot.writeBool(struct.with_ack);
      oprot.writeFieldEnd();
      oprot.writeFieldBegin(DURABLE_FIELD_DESC);
      oprot.writeBool(struct.durable);
      oprot.writeFieldEnd();
      oprot.writeFieldBegin(EXCLUSIVE_FIELD_DESC);
      oprot.writeBool(struct.exclusive);
      oprot.writeFieldEnd();
      oprot.writeFieldBegin(IGNR_MSG_PROB_FIELD_DESC);
      oprot.writeDouble(struct.ignr_msg_prob);
      oprot.writeFieldEnd();
      oprot.writeFieldStop();
      oprot.writeStructEnd();
    }

  }

  private static class TriggerInfoAMQPTupleSchemeFactory implements org.apache.thrift.scheme.SchemeFactory {
    public TriggerInfoAMQPTupleScheme getScheme() {
      return new TriggerInfoAMQPTupleScheme();
    }
  }

  private static class TriggerInfoAMQPTupleScheme extends org.apache.thrift.scheme.TupleScheme<TriggerInfoAMQP> {

    @Override
    public void write(org.apache.thrift.protocol.TProtocol prot, TriggerInfoAMQP struct) throws org.apache.thrift.TException {
      org.apache.thrift.protocol.TTupleProtocol oprot = (org.apache.thrift.protocol.TTupleProtocol) prot;
      java.util.BitSet optionals = new java.util.BitSet();
      if (struct.isSetAmqp_addr()) {
        optionals.set(0);
      }
      if (struct.isSetRouting_key()) {
        optionals.set(1);
      }
      if (struct.isSetExchange()) {
        optionals.set(2);
      }
      if (struct.isSetWith_ack()) {
        optionals.set(3);
      }
      if (struct.isSetDurable()) {
        optionals.set(4);
      }
      if (struct.isSetExclusive()) {
        optionals.set(5);
      }
      if (struct.isSetIgnr_msg_prob()) {
        optionals.set(6);
      }
      oprot.writeBitSet(optionals, 7);
      if (struct.isSetAmqp_addr()) {
        oprot.writeString(struct.amqp_addr);
      }
      if (struct.isSetRouting_key()) {
        oprot.writeString(struct.routing_key);
      }
      if (struct.isSetExchange()) {
        oprot.writeString(struct.exchange);
      }
      if (struct.isSetWith_ack()) {
        oprot.writeBool(struct.with_ack);
      }
      if (struct.isSetDurable()) {
        oprot.writeBool(struct.durable);
      }
      if (struct.isSetExclusive()) {
        oprot.writeBool(struct.exclusive);
      }
      if (struct.isSetIgnr_msg_prob()) {
        oprot.writeDouble(struct.ignr_msg_prob);
      }
    }

    @Override
    public void read(org.apache.thrift.protocol.TProtocol prot, TriggerInfoAMQP struct) throws org.apache.thrift.TException {
      org.apache.thrift.protocol.TTupleProtocol iprot = (org.apache.thrift.protocol.TTupleProtocol) prot;
      java.util.BitSet incoming = iprot.readBitSet(7);
      if (incoming.get(0)) {
        struct.amqp_addr = iprot.readString();
        struct.setAmqp_addrIsSet(true);
      }
      if (incoming.get(1)) {
        struct.routing_key = iprot.readString();
        struct.setRouting_keyIsSet(true);
      }
      if (incoming.get(2)) {
        struct.exchange = iprot.readString();
        struct.setExchangeIsSet(true);
      }
      if (incoming.get(3)) {
        struct.with_ack = iprot.readBool();
        struct.setWith_ackIsSet(true);
      }
      if (incoming.get(4)) {
        struct.durable = iprot.readBool();
        struct.setDurableIsSet(true);
      }
      if (incoming.get(5)) {
        struct.exclusive = iprot.readBool();
        struct.setExclusiveIsSet(true);
      }
      if (incoming.get(6)) {
        struct.ignr_msg_prob = iprot.readDouble();
        struct.setIgnr_msg_probIsSet(true);
      }
    }
  }

  private static <S extends org.apache.thrift.scheme.IScheme> S scheme(org.apache.thrift.protocol.TProtocol proto) {
    return (org.apache.thrift.scheme.StandardScheme.class.equals(proto.getScheme()) ? STANDARD_SCHEME_FACTORY : TUPLE_SCHEME_FACTORY).getScheme();
  }
}

