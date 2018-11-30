import seaborn as sns
import matplotlib.pyplot as plt


def graph_yearly_model_performance(year_data_frame, error=True):
    if error:
        # MAE scores
        plt.figure(figsize=(15, 9))
        sns.barplot(x='year', y='error', hue='model', data=year_data_frame)
        # Not starting axis at 0 to make small relative differences clearer
        plt.ylim(bottom=20)
        plt.title('Model error per season\n', fontsize=18)
        plt.ylabel('MAE', fontsize=14)
        plt.xlabel('', fontsize=14)
        plt.yticks(fontsize=12)
        plt.xticks(fontsize=12)
        plt.legend(fontsize=14)

        plt.show()

    # Accuracy scores
    plt.figure(figsize=(15, 8))
    sns.barplot(x='year', y='accuracy', hue='model', data=year_data_frame)
    # Not starting axis at 0 to make small relative differences clearer
    plt.ylim(bottom=0.55)
    plt.title('Model accuracy per season\n', fontsize=18)
    plt.ylabel('Accuracy', fontsize=14)
    plt.xlabel('', fontsize=14)
    plt.yticks(fontsize=12)
    plt.xticks(fontsize=12, rotation=90)
    plt.legend(fontsize=14)

    plt.show()


def graph_tf_model_history(history):
    acc = history.history['tip_accuracy']
    val_acc = history.history['val_tip_accuracy']
    loss = history.history['loss']
    val_loss = history.history['val_loss']

    epochs = range(len(loss))

    plt.plot(epochs, acc, 'bo', label='Training acc')
    plt.plot(epochs, val_acc, 'b', label='Validation acc')
    plt.title('Training and validation accuracy')
    plt.legend()

    plt.figure()

    plt.plot(epochs, loss, 'bo', label='Training loss')
    plt.plot(epochs, val_loss, 'b', label='Validation loss')
    plt.title('Training and validation loss')
    plt.legend()

    plt.show()
