from itertools import islice


def chunk_list(list_to_split: list,
               chunk_size: int):
    list_to_split = iter(list_to_split)
    res = iter(lambda: list(islice(list_to_split, chunk_size)), list())
    return list(res)