import argparse
import collections
import os
import random
from operator import itemgetter

import chainer
from chainer import optimizers

from ast_tree.ast_parser import split_trees2
# from deep_ast.tree_lstm.treelstm import TreeLSTM
from chainer import serializers
from models.lstm_models import RecursiveHighWayLSTM, RecursiveLSTM, RecursiveBiLSTM, RecursiveResidualLSTM
from models.tree_models import RecursiveTreeLSTM
from utils.exp_utlis import pick_subsets, split_trees,train,evaluate
from utils.fun_utils import parse_src_files, print_model


def print_table(table):
    col_width = [max(len(x) for x in col) for col in zip(*table)]
    for line in table:
        print("| " + " | ".join("{:{}}".format(x, col_width[i])
                                for i, x in enumerate(line)) + " |")

def main_experiment():
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', '-n', type=str, default="default_experiment", help='Experiment name')
    parser.add_argument('--dataset', '-d', type=str, default="dataset/dataset700", help='Experiment dataset')
    parser.add_argument('--classes', '-c', type=int, default=2, help='How many classes to include in this experiment')
    parser.add_argument('--gpu', '-g', type=int, default=-1, help='GPU ID (negative value indicates CPU)')
    parser.add_argument('--folder', '-f', type=str, default="", help='Base folder for logs and results')
    parser.add_argument('--batchsize', '-b', type=int, default=1, help='Number of examples in each mini batch')
    parser.add_argument('--layers', '-l', type=int, default=2, help='Number of Layers for LSTMs')
    parser.add_argument('--dropout', '-dr', type=float, default=0.2, help='Number of Layers for LSTMs')

    parser.add_argument('--model', '-m', type=str, default="lstm", help='Model used for this experiment')
    parser.add_argument('--units', '-u', type=int, default=100, help='Number of hidden units')
    parser.add_argument('--save', '-s', type=int, default=1, help='Save best models')

    args = parser.parse_args()

    n_epoch = 500
    n_units = args.units
    batch_size = args.batchsize
    gpu = args.gpu
    models_base_folder = "saved_models"
    output_folder = os.path.join("results",args.folder)  # args.folder  #R"C:\Users\bms\PycharmProjects\stylemotery_code" #
    exper_name = args.name
    dataset_folder = args.dataset
    model_name = args.model
    layers = args.layers
    dropout = args.dropout
    rand_seed = random.randint(0, 4294967295)

    output_file = open(os.path.join(output_folder, exper_name + "_results.txt"), mode="+w")
    output_file.write("Testing the model on all the datasets\n")
    output_file.write("Args :- " + str(args) + "\n")
    output_file.write("Seed :- " + str(rand_seed) + "\n")

    trees, tree_labels, lable_problems = parse_src_files(dataset_folder)
    if args.classes > -1:
        trees, tree_labels = pick_subsets(trees, tree_labels, labels=args.classes,seed=rand_seed)
    train_trees, train_lables, test_trees, test_lables, classes, cv = split_trees(trees, tree_labels, n_folds=5,
                                                                                  shuffle=True,seed=rand_seed)
    #if args.subtrees > -1:
    #    train_trees, train_lables, _ = split_trees2(train_trees, train_lables,lable_problems, original=True)

    output_file.write("Classes :- (%s)\n" % [(idx, c) for idx, c in enumerate(classes)])
    output_file.write("Class ratio :- %s\n" % list(
        sorted([(t, c, c / len(tree_labels)) for t, c in collections.Counter(tree_labels).items()], key=itemgetter(0),
               reverse=False)))
    output_file.write("Cross Validation :-%s\n" % cv)
    output_file.write("Train labels :- (%s,%s%%): %s\n" % (
    len(train_lables), (len(train_lables) / len(tree_labels)) * 100, train_lables))
    output_file.write(
        "Test  labels :- (%s,%s%%): %s\n" % (len(test_lables), (len(test_lables) / len(tree_labels)) * 100, test_lables))

    if model_name == "lstm":
        model = RecursiveLSTM(n_units, len(classes), layers=layers, dropout=dropout, classes=classes, peephole=False)
    elif model_name == "bilstm":
        model = RecursiveBiLSTM(n_units, len(classes), dropout=dropout, classes=classes,peephole=False)
    elif model_name == "biplstm":
        model = RecursiveBiLSTM(n_units, len(classes), dropout=dropout, classes=classes,peephole=True)
    elif model_name == "plstm":
        model = RecursiveLSTM(n_units, len(classes), layers=layers, dropout=dropout, classes=classes, peephole=True)
    elif model_name == "highway":
        model = RecursiveHighWayLSTM(n_units, len(classes),layers=layers, dropout=dropout, classes=classes, peephole=False)
    elif model_name == "reslstm":
        model = RecursiveResidualLSTM(n_units, len(classes),layers=layers, dropout=dropout, classes=classes, peephole=False)
    elif model_name == "treestm":
        model = RecursiveTreeLSTM(2, n_units, len(classes), classes=classes)
    else:
        print("No model was found")
        return

    output_file.write("Model:  {0}\n".format(exper_name))
    output_file.write("Params: {:,} \n".format(model.params_count()))
    output_file.write("        {0} \n".format(type(model).__name__))
    print_model(model, depth=1, output=output_file)

    if gpu >= 0:
        model.to_gpu()

    # Setup optimizer
    optimizer = optimizers.MomentumSGD(lr=0.01, momentum=0.9)#Adam(alpha=0.001, beta1=0.9, beta2=0.999, eps=1e-08)#AdaGrad(lr=0.01)#NesterovAG(lr=0.01, momentum=0.9)#AdaGrad(lr=0.01) # MomentumSGD(lr=0.01, momentum=0.9)  # AdaGrad(lr=0.1) #
    output_file.write("Optimizer: {0} ".format((type(optimizer).__name__, optimizer.__dict__)))
    optimizer.setup(model)
    optimizer.add_hook(chainer.optimizer.WeightDecay(0.001))
    optimizer.add_hook(chainer.optimizer.GradientClipping(10.0))

    hooks = [(k, v.__dict__) for k, v in optimizer._hooks.items()]
    output_file.write(" {0} \n".format(hooks))

    output_file.write("Evaluation\n")
    output_file.write("{0:<10}{1:<20}{2:<20}{3:<20}{4:<20}\n".format("epoch", "train_loss", "test_loss","train_accuracy", "test_accuracy"))
    output_file.flush()

    best_scores = (-1, -1, -1)  # (epoch, loss, accuracy)
    for epoch in range(1, n_epoch + 1):
        print('Epoch: {0:d} / {1:d}'.format(epoch, n_epoch))
        print("optimizer lr = ", optimizer.lr)
        print('Train')
        training_accuracy, training_loss = train(model, train_trees, train_lables, optimizer, batch_size, shuffle=True)
        print('Test')
        test_accuracy, test_loss = evaluate(model, test_trees, test_lables, batch_size)
        print()

        # save the best models
        saved = False
        if args.save > 0 and epoch > 0:
            epoch_, loss_, acc_ = best_scores
            # save the model with best accuracy or same accuracy and less loss
            if test_accuracy > acc_ or (test_accuracy >= acc_ and test_loss <= loss_):
                # remove last saved model
                model_saved_name = "{0}_epoch_{1}.my".format(exper_name, epoch_)
                path = os.path.join(models_base_folder, model_saved_name)
                if os.path.exists(path):
                    os.remove(path)
                # save models
                model_saved_name = "{0}_epoch_{1}.my".format(exper_name, epoch)
                path = os.path.join(models_base_folder, model_saved_name)
                serializers.save_npz(path, model)
                # save optimizer
                model_saved_name = "{0}_epoch_{1}.opt".format(exper_name, epoch)
                path = os.path.join(models_base_folder, model_saved_name)
                serializers.save_npz(path, optimizer)
                saved = True
                print("saving ... ")
                best_scores = (epoch, test_loss, test_accuracy)

        output_file.write(
            "{0:<10}{1:<20.10f}{2:<20.10f}{3:<20.10f}{4:<20.10f}{5:<10}\n".format(epoch, training_loss, test_loss,
                                                                                  training_accuracy, test_accuracy,
                                                                                  "saved" if saved else ""))
        output_file.flush()

        if epoch >= 5 and (test_loss < 0.001 or test_accuracy >= 1.0):
            output_file.write("\tEarly Stopping\n")
            print("\tEarly Stopping")
            break

            # if epoch is 3:
            #     lr = optimizer.lr
            #     setattr(optimizer, 'lr', lr / 10)

    output_file.close()


if __name__ == "__main__":
    main_experiment()
