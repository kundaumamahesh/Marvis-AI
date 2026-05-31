import matplotlib.pyplot as plt

class ChartEngine:

    @staticmethod
    def create_chart():

        x = [1,2,3,4]
        y = [10,20,15,40]

        plt.figure(figsize=(8,4))

        plt.plot(x, y)

        plt.savefig(
            "outputs/images/chart.png"
        )
