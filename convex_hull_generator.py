# NOTE: COPIED FROM https://github.com/vshallc/PtrNets/blob/master/pointer/misc/convex_hull.py
import numpy
from scipy.spatial import ConvexHull


def generate_one_example(n_nodes):
    points = numpy.random.rand(n_nodes, 2)
    hull = ConvexHull(points)  # scipy.spatial.ConvexHull will generate points in CCW order
    v = hull.vertices
    # v = numpy.roll(v, -list(v).index(numpy.min(v)))  # start from the smallest indice
    return points, v + 1


def generate_examples(num, n_min, n_max):
    examples = []
    for i in range(num):
        n_nodes = numpy.random.randint(n_min, n_max + 1)
        nodes, res = generate_one_example(n_nodes)
        examples.append((nodes, res))
    return examples


if __name__ == '__main__':
    # planar convex hull
#     size = '5-50-large'
#     size = '5-small'
    size = '5-tiny'
    
    if size == '5-50-large':
        e_train = generate_examples(1048576, 5, 50)
        e_valid = generate_examples(1000, 5, 50)
        e_test = generate_examples(1000, 50, 50)
    if size == '5-small':
        e_train = generate_examples(100000, 5, 5)
        e_valid = generate_examples(1000, 5, 5)
        e_test = generate_examples(1000, 5, 5)
    if size == '5-tiny':
        e_train = generate_examples(100, 5, 5)
        e_valid = generate_examples(100, 5, 5)
        e_test = generate_examples(100, 5, 5)
        
    obj = (e_train, e_valid, e_test)

    numpy.savez_compressed('convex_hull_{}.npz'.format(size), obj)