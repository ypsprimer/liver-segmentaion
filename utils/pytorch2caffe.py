import sys

sys.path.append("/data/temp/caffe/python")
import caffe
from collections import OrderedDict
import numpy as np

try:
    import caffe.proto.caffe_pb2 as caffe_pb2
except:
    try:
        import caffe_pb2
    except:
        print "caffe_pb2.py not found. Try:"
        print "  protoc caffe.proto --python_out=."
        exit()


layer_dict = {
    "ConvNdBackward": "Convolution",
    "ThresholdBackward": "ReLU",
    "MaxPool2dBackward": "Pooling",
    "AvgPool2dBackward": "Pooling",
    "DropoutBackward": "Dropout",
    "AddmmBackward": "InnerProduct",
    "BatchNormBackward": "BatchNorm",
    "AddBackward": "Eltwise",
    "SoftmaxBackward": "Softmax",
    "ViewBackward": "Reshape",
}

layer_id = 0


def parse_caffemodel(caffemodel):
    model = caffe_pb2.NetParameter()
    print "Loading caffemodel: ", caffemodel
    with open(caffemodel, "rb") as fp:
        model.ParseFromString(fp.read())

    return model


def parse_prototxt(protofile):
    def line_type(line):
        if line.find(":") >= 0:
            return 0
        elif line.find("{") >= 0:
            return 1
        return -1

    def parse_block(fp):
        block = OrderedDict()
        line = fp.readline().strip()
        while line != "}":
            ltype = line_type(line)
            if ltype == 0:  # key: value
                # print line
                line = line.split("#")[0]
                key, value = line.split(":")
                key = key.strip()
                value = value.strip().strip('"')
                if block.has_key(key):
                    if type(block[key]) == list:
                        block[key].append(value)
                    else:
                        block[key] = [block[key], value]
                else:
                    block[key] = value
            elif ltype == 1:  # blockname {
                key = line.split("{")[0].strip()
                sub_block = parse_block(fp)
                block[key] = sub_block
            line = fp.readline().strip()
            line = line.split("#")[0]
        return block

    fp = open(protofile, "r")
    props = OrderedDict()
    layers = []
    line = fp.readline()
    while line != "":
        line = line.strip().split("#")[0]
        if line == "":
            line = fp.readline()
            continue
        ltype = line_type(line)
        if ltype == 0:  # key: value
            key, value = line.split(":")
            key = key.strip()
            value = value.strip().strip('"')
            if props.has_key(key):
                if type(props[key]) == list:
                    props[key].append(value)
                else:
                    props[key] = [props[key], value]
            else:
                props[key] = value
        elif ltype == 1:  # blockname {
            key = line.split("{")[0].strip()
            if key == "layer":
                layer = parse_block(fp)
                layers.append(layer)
            else:
                props[key] = parse_block(fp)
        line = fp.readline()

    if len(layers) > 0:
        net_info = OrderedDict()
        net_info["props"] = props
        net_info["layers"] = layers
        return net_info
    else:
        return props


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False


def print_prototxt(net_info):
    # whether add double quote
    def format_value(value):
        # str = u'%s' % value
        # if str.isnumeric():
        if is_number(value):
            return value
        elif (
            value == "true"
            or value == "false"
            or value == "MAX"
            or value == "SUM"
            or value == "AVE"
        ):
            return value
        else:
            return '"%s"' % value

    def print_block(block_info, prefix, indent):
        blanks = "".join([" "] * indent)
        print ("%s%s {" % (blanks, prefix))
        for key, value in block_info.items():
            if type(value) == OrderedDict:
                print_block(value, key, indent + 4)
            elif type(value) == list:
                for v in value:
                    print ("%s    %s: %s" % (blanks, key, format_value(v)))
            else:
                print ("%s    %s: %s" % (blanks, key, format_value(value)))
        print ("%s}" % blanks)

    props = net_info["props"]
    layers = net_info["layers"]
    print ('name: "%s"' % props["name"])
    print ('input: "%s"' % props["input"])
    print ("input_dim: %s" % props["input_dim"][0])
    print ("input_dim: %s" % props["input_dim"][1])
    print ("input_dim: %s" % props["input_dim"][2])
    print ("input_dim: %s" % props["input_dim"][3])
    print ("")
    for layer in layers:
        print_block(layer, "layer", 0)


def save_prototxt(net_info, protofile, region=True):
    fp = open(protofile, "w")

    # whether add double quote
    def format_value(value):
        # str = u'%s' % value
        # if str.isnumeric():
        if is_number(value):
            return value
        elif (
            value == "true"
            or value == "false"
            or value == "MAX"
            or value == "SUM"
            or value == "AVE"
        ):
            return value
        else:
            return '"%s"' % value

    def print_block(block_info, prefix, indent):
        blanks = "".join([" "] * indent)
        print >> fp, "%s%s {" % (blanks, prefix)
        for key, value in block_info.items():
            if type(value) == OrderedDict:
                print_block(value, key, indent + 4)
            elif type(value) == list:
                for v in value:
                    print >> fp, "%s    %s: %s" % (blanks, key, format_value(v))
            else:
                print >> fp, "%s    %s: %s" % (blanks, key, format_value(value))
        print >> fp, "%s}" % blanks

    props = net_info["props"]
    layers = net_info["layers"]
    print >> fp, 'name: "%s"' % props["name"]
    print >> fp, 'input: "%s"' % props["input"]
    print >> fp, "input_dim: %s" % props["input_dim"][0]
    print >> fp, "input_dim: %s" % props["input_dim"][1]
    print >> fp, "input_dim: %s" % props["input_dim"][2]
    print >> fp, "input_dim: %s" % props["input_dim"][3]
    print >> fp, ""
    for layer in layers:
        if layer["type"] != "Region" or region == True:
            print_block(layer, "layer", 0)
    fp.close()


def pytorch2caffe(input_var, output_var, protofile, caffemodel):
    global layer_id
    net_info = pytorch2prototxt(input_var, output_var)
    print_prototxt(net_info)
    save_prototxt(net_info, protofile)

    net = caffe.Net(protofile, caffe.TEST)
    params = net.params

    layer_id = 1
    seen = set()

    def convert_layer(func):
        if True:
            global layer_id
            parent_type = str(type(func).__name__)

            if hasattr(func, "next_functions"):
                for u in func.next_functions:
                    if u[0] is not None:
                        child_type = str(type(u[0]).__name__)
                        child_name = child_type + str(layer_id)
                        if child_type != "AccumulateGrad" and (
                            parent_type != "AddmmBackward"
                            or child_type != "TransposeBackward"
                        ):
                            if u[0] not in seen:
                                convert_layer(u[0])
                                seen.add(u[0])
                            if child_type != "ViewBackward":
                                layer_id = layer_id + 1

            parent_name = parent_type + str(layer_id)
            print ("converting %s" % parent_name)
            if parent_type == "ConvNdBackward":
                weights = func.next_functions[1][0].variable.data
                if func.next_functions[2][0]:
                    biases = func.next_functions[2][0].variable.data
                else:
                    biases = None
                save_conv2caffe(weights, biases, params[parent_name])
            elif parent_type == "BatchNormBackward":
                running_mean = func.running_mean
                running_var = func.running_var
                # print('%s running_mean' % parent_name, running_mean)
                # exit(0)
                scale_weights = func.next_functions[1][0].variable.data
                scale_biases = func.next_functions[2][0].variable.data
                bn_name = parent_name + "_bn"
                scale_name = parent_name + "_scale"
                save_bn2caffe(running_mean, running_var, params[bn_name])
                save_scale2caffe(scale_weights, scale_biases, params[scale_name])
            elif parent_type == "AddmmBackward":
                biases = func.next_functions[0][0].variable.data
                weights = func.next_functions[2][0].next_functions[0][0].variable.data
                save_fc2caffe(weights, biases, params[parent_name])

    convert_layer(output_var.grad_fn)
    print ("save caffemodel to %s" % caffemodel)
    net.save(caffemodel)


def save_conv2caffe(weights, biases, conv_param):
    if biases is not None:
        conv_param[1].data[...] = biases.numpy()
    conv_param[0].data[...] = weights.numpy()


def save_fc2caffe(weights, biases, fc_param):
    fc_param[1].data[...] = biases.numpy()
    fc_param[0].data[...] = weights.numpy()


def save_bn2caffe(running_mean, running_var, bn_param):
    bn_param[0].data[...] = running_mean.numpy()
    bn_param[1].data[...] = running_var.numpy()
    bn_param[2].data[...] = np.array([1.0])


def save_scale2caffe(weights, biases, scale_param):
    scale_param[1].data[...] = biases.numpy()
    scale_param[0].data[...] = weights.numpy()


# def pytorch2prototxt(model, x, var):
def pytorch2prototxt(input_var, output_var):
    global layer_id
    net_info = OrderedDict()
    props = OrderedDict()
    props["name"] = "pytorch"
    props["input"] = "data"
    props["input_dim"] = input_var.size()

    layers = []

    layer_id = 1
    seen = set()
    top_names = dict()

    def add_layer(func):
        global layer_id
        parent_type = str(type(func).__name__)
        parent_bottoms = []

        if hasattr(func, "next_functions"):
            for u in func.next_functions:
                if u[0] is not None:
                    child_type = str(type(u[0]).__name__)
                    child_name = child_type + str(layer_id)
                    if child_type != "AccumulateGrad" and (
                        parent_type != "AddmmBackward"
                        or child_type != "TransposeBackward"
                    ):
                        if u[0] not in seen:
                            top_name = add_layer(u[0])
                            parent_bottoms.append(top_name)
                            seen.add(u[0])
                        else:
                            top_name = top_names[u[0]]
                            parent_bottoms.append(top_name)
                        if child_type != "ViewBackward":
                            layer_id = layer_id + 1

        parent_name = parent_type + str(layer_id)
        layer = OrderedDict()
        layer["name"] = parent_name
        layer["type"] = layer_dict[parent_type]
        parent_top = parent_name
        if len(parent_bottoms) > 0:
            layer["bottom"] = parent_bottoms
        else:
            layer["bottom"] = ["data"]
        layer["top"] = parent_top
        if parent_type == "ConvNdBackward":
            weights = func.next_functions[1][0].variable
            conv_param = OrderedDict()
            conv_param["num_output"] = weights.size(0)
            conv_param["pad"] = func.padding[0]
            conv_param["kernel_size"] = weights.size(2)
            conv_param["stride"] = func.stride[0]
            if func.next_functions[2][0] == None:
                conv_param["bias_term"] = "false"
            layer["convolution_param"] = conv_param
        elif parent_type == "BatchNormBackward":
            bn_layer = OrderedDict()
            bn_layer["name"] = parent_name + "_bn"
            bn_layer["type"] = "BatchNorm"
            bn_layer["bottom"] = parent_bottoms
            bn_layer["top"] = parent_top
            batch_norm_param = OrderedDict()
            batch_norm_param["use_global_stats"] = "true"
            bn_layer["batch_norm_param"] = batch_norm_param

            scale_layer = OrderedDict()
            scale_layer["name"] = parent_name + "_scale"
            scale_layer["type"] = "Scale"
            scale_layer["bottom"] = parent_top
            scale_layer["top"] = parent_top
            scale_param = OrderedDict()
            scale_param["bias_term"] = "true"
            scale_layer["scale_param"] = scale_param
        elif parent_type == "ThresholdBackward":
            parent_top = parent_bottoms[0]
        elif parent_type == "SoftmaxBackward":
            parent_top = parent_bottoms[0]
        elif parent_type == "MaxPool2dBackward":
            pooling_param = OrderedDict()
            pooling_param["pool"] = "MAX"
            pooling_param["kernel_size"] = func.kernel_size[0]
            pooling_param["stride"] = func.stride[0]
            pooling_param["pad"] = func.padding[0]
            layer["pooling_param"] = pooling_param
        elif parent_type == "AvgPool2dBackward":
            pooling_param = OrderedDict()
            pooling_param["pool"] = "AVE"
            pooling_param["kernel_size"] = func.kernel_size[0]
            pooling_param["stride"] = func.stride[0]
            layer["pooling_param"] = pooling_param
        elif parent_type == "DropoutBackward":
            parent_top = parent_bottoms[0]
            dropout_param = OrderedDict()
            dropout_param["dropout_ratio"] = func.p
            layer["dropout_param"] = dropout_param
        elif parent_type == "AddmmBackward":
            inner_product_param = OrderedDict()
            inner_product_param["num_output"] = func.next_functions[0][0].variable.size(
                0
            )
            layer["inner_product_param"] = inner_product_param
        elif parent_type == "ViewBackward":
            parent_top = parent_bottoms[0]
        elif parent_type == "AddBackward":
            eltwise_param = OrderedDict()
            eltwise_param["operation"] = "SUM"
            layer["eltwise_param"] = eltwise_param

        layer["top"] = parent_top  # reset layer['top'] as parent_top may change
        if parent_type != "ViewBackward":
            if parent_type == "BatchNormBackward":
                layers.append(bn_layer)
                layers.append(scale_layer)
            else:
                layers.append(layer)
                # layer_id = layer_id + 1
        top_names[func] = parent_top
        return parent_top

    add_layer(output_var.grad_fn)
    net_info["props"] = props
    net_info["layers"] = layers
    return net_info


if __name__ == "__main__":
    from models import SKUNET
    import torch
    from torch.autograd import Variable

    m = SKUNET()
    m.classifier.add_module("softmax", torch.nn.Softmax())
    m.eval()  # very important here, otherwise batchnorm running_mean, running_var will be incorrect
    input_var = Variable(torch.rand(1, 3, 224, 224))

    print (m)
    output_var = m(input_var)
    fp = open("out.dot", "w")
    print >> fp
    fp.close()
    # exit(0)

    pytorch2caffe(
        input_var,
        output_var,
        "skunet-pytorch2caffe.prototxt",
        "skunet-pytorch2caffe.caffemodel",
    )
