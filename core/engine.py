import time
import math
import hashlib
import struct
import zlib
import bisect

from lxml import etree

PAGE_TOKEN_PREFIX = 'WikipediaPageTokenUniqleQQQQQQQQQ'
HASH_LENGTH = 128
INTEGER_LENGTH = 4
WIKI_LINK_PREFIX_LENGTH = 32
JUMP_TABLE_SPACE_BYTES = 4*256*1
CREATE_JUMP_TABLE_MIN_BYTES = JUMP_TABLE_SPACE_BYTES * 8
STATES_NUMBER_IN_SERP = 50
SNIPPET_WINDOW_SIZE = 3
SNIPPET_LINE_LENGTH = 120
SNIPPET_LINE_NUMBER = 3
TITLE_TF_IDF_WEIGHT = 0.12


def parse_wiki_xml(xml_file_name, result_data_name):
    xml = open(xml_file_name, 'r', encoding='utf-8').read()

    parser = etree.XMLParser(encoding='utf-8')
    root = etree.fromstring(xml, parser=parser)
    result = open(result_data_name, 'w', encoding='utf-8')

    number = 0
    for elem in root.getchildren():
        title = ''
        text = ''
        id_page = ''

        if elem.tag[elem.tag.find('}')+1:] == 'page':
            number += 1

            for el in elem.getchildren():
                if el.tag[el.tag.find('}')+1:] == 'title':
                    title = el.text
                elif el.tag[el.tag.find('}')+1:] == 'id':
                    id_page = el.text
                elif el.tag[el.tag.find('}')+1:] == 'revision':
                    for e in el.getchildren():
                        if e.tag[e.tag.find('}')+1:] == 'text':
                            text = e.text

            result.write('\n\n' + PAGE_TOKEN_PREFIX + id_page + '\n\n' + title + '\n\n' + text)
    result.close()


def tokenization(data_file_name, result_file_name):
    data = open(data_file_name, 'r', encoding='utf-8')
    result = open(result_file_name, 'w', encoding='utf-8')

    print('begin')
    for line in data:
        res = ''
        for i in range(len(line)):
            if line[i].isalpha() or line[i].isdigit():
                res += line[i]
            else:
                res += ' '
        result.write(res + '\n')
    print('end')
    data.close()
    result.close()


def test_tokenization():
    number_test = ['16', '8', '4', '2', '1']
    test_prefix = '../test_tokens/data_1_'

    for i in range(len(number_test)):
        start_time = time.time()
        tokenization(test_prefix + number_test[i] + '.txt', 'tokens.txt')
        print(test_prefix + number_test[i] + '.txt:', time.time() - start_time)


def P(assessment):
    result = 0
    for r in assessment:
        if r > 3:
            result += 1
    return result / len(assessment)


def to_format(number, precision=2):
    return format(number, '.'+str(precision)+'f')


def hash_used(token):
    return hashlib.sha512(bytes(token, 'utf-8')).hexdigest()


def indexation(token_file_name, dictionary_file_name, inverse_index_file_name, straight_index_file_name,
               coordinate_file_name, jump_table_file_name, inverse_title_index_file_name, coordinate_title_file_name,
               test=False, stats=False):
    token_file = open(token_file_name, 'r', encoding='utf-8')
    dictionary_file = open(dictionary_file_name, 'wb')
    inverse_index_file = open(inverse_index_file_name, 'wb')
    straight_index_file = open(straight_index_file_name, 'wb')
    coordinate_file = open(coordinate_file_name, 'wb')
    jump_table_file = open(jump_table_file_name, 'wb')
    inverse_title_index_file = open(inverse_title_index_file_name, 'wb')
    coordinate_title_file = open(coordinate_title_file_name, 'wb')

    all_tokens = set()
    dictionary = dict()
    dictionary_title = dict()
    coordinates = dict()
    coordinates_title = dict()
    straight_index_data = []
    id_page = -1
    wiki_link_prefix = 'https://ru.wikipedia.org/?curid='
    title_now = 0
    coordinate = 0
    line = token_file.readline()
    while line:
        if title_now != 0:
            title_now += 1
        if title_now == 3:
            straight_index_data[-1][2] = line
            title_now = 0
            coordinate_title = 0
            tokens = line.split()
            for token in tokens:
                token = token.lower()
                token = remove_rus_ending(token)

                all_tokens.add(token)
                if token not in coordinates_title:
                    coordinates_title[token] = dict()
                if id_page not in coordinates_title[token].keys():
                    coordinates_title[token][id_page] = []
                    coordinates_title[token][id_page].append(coordinate_title)
                if token in dictionary_title.keys() and dictionary_title[token][-1] != id_page:
                    dictionary_title[token].append(id_page)
                elif token not in dictionary_title.keys():
                    dictionary_title[token] = [id_page]
                    coordinate_title += 1
            line = token_file.readline()
            continue
        if line.startswith(PAGE_TOKEN_PREFIX):
            line = line.replace(PAGE_TOKEN_PREFIX, '')
            id_page = int(line)
            straight_index_data.append([id_page, wiki_link_prefix+str(id_page), '', token_file.tell()])
            title_now = 1
            coordinate = 0
        else:
            tokens = line.split()
            for token in tokens:
                token = token.lower()
                token = remove_rus_ending(token)

                all_tokens.add(token)
                if token not in coordinates:
                    coordinates[token] = dict()
                if id_page not in coordinates[token].keys():
                    coordinates[token][id_page] = []
                coordinates[token][id_page].append(coordinate)
                if token in dictionary.keys() and dictionary[token][-1] != id_page:
                    dictionary[token].append(id_page)
                elif token not in dictionary.keys():
                    dictionary[token] = [id_page]
                coordinate += 1
        line = token_file.readline()

    dictionary_data = []
    inverse_index_file_offset = 0
    inverse_index_title_file_offset = 0
    jump_table_file_offset = 0
    for key in all_tokens:
        elem = [hash_used(key)]
        if key in dictionary.keys():
            dictionary[key].sort()
            elem.extend([len(dictionary[key]), 0, dictionary[key], coordinates[key], 0])
        else:
            elem.extend([0, 0, [], [], 0])
        if key in dictionary_title.keys():
            dictionary_title[key].sort()
            elem.extend([0, dictionary_title[key], coordinates_title[key]])
        else:
            elem.extend([0, [], []])
        dictionary_data.append(elem)

    dictionary_data.sort(key=lambda a: a[0])
    coordinates_offset = 0
    coordinates_title_offset = 0
    for i in range(len(dictionary_data)):
        hash_value, number_ids, offset, page_ids, token_coordinates, jump_table_offset, \
            offset_title, page_ids_title, coordinates_title = dictionary_data[i]
        offsets_coordinate_index_file = []
        offsets_coordinate_title_index_file = []

        def sorted_list_to_difference(data):
            if len(data) == 1:
                return []

            result = []
            for i in range(1, len(data)):
                result.append(data[i] - data[i - 1])
            return result

        if len(page_ids) > 0:
            dictionary_data[i][2] = inverse_index_file_offset

            for page_id in page_ids:
                offsets_coordinate_index_file.append(coordinates_offset)

                coordinates_difference = sorted_list_to_difference(token_coordinates[page_id])

                coordinate_file.write(struct.pack('i', len(token_coordinates[page_id])))
                coordinate_file.write(struct.pack('i', token_coordinates[page_id][0]))
                compressed_coordinates_difference = simple9_encode(coordinates_difference)
                coordinate_file.write(struct.pack('i', len(compressed_coordinates_difference)))

                if len(compressed_coordinates_difference) > 0:
                    coordinate_file.write(compressed_coordinates_difference)

                coordinates_offset += INTEGER_LENGTH * 3 + len(compressed_coordinates_difference)

            compressed_page_ids, jump_table_info = simple9_encode(sorted_list_to_difference(page_ids),
                                                                  jump_table_info_need=True)
            compressed_coordinate_offsets = simple9_encode(sorted_list_to_difference(offsets_coordinate_index_file))

            inverse_index_file.write(struct.pack('i', page_ids[0]))
            inverse_index_file.write(struct.pack('i', len(compressed_page_ids)))
            inverse_index_file.write(compressed_page_ids)

            inverse_index_file.write(struct.pack('i', offsets_coordinate_index_file[0]))
            inverse_index_file.write(struct.pack('i', len(compressed_coordinate_offsets)))
            inverse_index_file.write(compressed_coordinate_offsets)

            if len(compressed_page_ids) > CREATE_JUMP_TABLE_MIN_BYTES:
                dictionary_data[i][5] = jump_table_file_offset
                jump_table_info = [[page_ids[x+1], y + inverse_index_file_offset + INTEGER_LENGTH * 2]
                                   for x, y in jump_table_info]
                compressed_jump_table_page_ids = simple9_encode(sorted_list_to_difference([x for x, y in jump_table_info]))
                jump_table_file.write(struct.pack('ii', jump_table_info[0][0], len(compressed_jump_table_page_ids)))
                jump_table_file.write(compressed_jump_table_page_ids)
                compressed_jump_table_offsets = simple9_encode(sorted_list_to_difference([y for x, y in jump_table_info]))
                jump_table_file.write(struct.pack('ii', jump_table_info[0][1], len(compressed_jump_table_offsets)))
                jump_table_file.write(compressed_jump_table_offsets)
                jump_table_file_offset += INTEGER_LENGTH * 4 + len(compressed_jump_table_page_ids) + \
                                          len(compressed_jump_table_offsets)
            else:
                dictionary_data[i][5] = -1

            inverse_index_file_offset += INTEGER_LENGTH * 4 + len(compressed_page_ids) + \
                                         len(compressed_coordinate_offsets)
        else:
            dictionary_data[i][2] = -1
            dictionary_data[i][5] = -1

        if len(page_ids_title) > 0:
            dictionary_data[i][6] = inverse_index_title_file_offset

            for page_id in page_ids_title:
                offsets_coordinate_title_index_file.append(coordinates_title_offset)

                coordinates_difference = sorted_list_to_difference(coordinates_title[page_id])

                coordinate_title_file.write(struct.pack('i', len(coordinates_title[page_id])))
                coordinate_title_file.write(struct.pack('i', coordinates_title[page_id][0]))
                compressed_title_coordinates_difference = simple9_encode(coordinates_difference)
                coordinate_title_file.write(struct.pack('i', len(compressed_title_coordinates_difference)))

                if len(compressed_title_coordinates_difference) > 0:
                    coordinate_title_file.write(compressed_title_coordinates_difference)

                coordinates_title_offset += INTEGER_LENGTH * 3 + len(compressed_title_coordinates_difference)

            compressed_page_ids_title = simple9_encode(sorted_list_to_difference(page_ids_title))
            compressed_coordinates_title_offsets = simple9_encode(
                sorted_list_to_difference(offsets_coordinate_title_index_file))

            inverse_title_index_file.write(struct.pack('i', page_ids_title[0]))
            inverse_title_index_file.write(struct.pack('i', len(compressed_page_ids_title)))
            inverse_title_index_file.write(compressed_page_ids_title)

            inverse_title_index_file.write(struct.pack('i', offsets_coordinate_title_index_file[0]))
            inverse_title_index_file.write(struct.pack('i', len(compressed_coordinates_title_offsets)))
            inverse_title_index_file.write(compressed_coordinates_title_offsets)

            inverse_index_title_file_offset += INTEGER_LENGTH * 4 + len(compressed_page_ids_title) + len(
                compressed_coordinates_title_offsets)
        else:
            dictionary_data[i][6] = -1

    dictionary_binary_data = []
    for hash_value, number_ids, offset, page_ids, token_coordinates, \
            jump_table_offset, offset_title, _, _ in dictionary_data:
        element = struct.pack(str(HASH_LENGTH)+'siiii', bytes(hash_value, 'utf-8'), number_ids,
                              offset, jump_table_offset, offset_title)
        dictionary_binary_data.append(element)

    dictionary_file.write(zlib.compress(b''.join(dictionary_binary_data), level=9))

    straight_index_data.sort(key=lambda a: a[0])
    straight_index_binary_data = []
    for page_id, link, title, state_offset in straight_index_data:
        link_length = len(bytes(link, 'utf-8'))
        title_length = len(bytes(title, 'utf-8'))
        element = struct.pack('iiii' + str(link_length) + 's' + str(title_length) + 's', page_id, state_offset,
                              link_length, title_length, bytes(link, 'utf-8'), bytes(title, 'utf-8'))
        straight_index_binary_data.append(element)

    straight_index_file.write(zlib.compress(b''.join(straight_index_binary_data), level=9))

    token_file.close()
    dictionary_file.close()
    inverse_index_file.close()
    straight_index_file.close()
    coordinate_file.close()
    jump_table_file.close()
    inverse_title_index_file.close()
    coordinate_title_file.close()

    if test:
        test_dictionary = dict()
        test_coordinates = dict()
        test_coordinates_title = dict()
        for hash_value, number_ids, offset, page_ids, token_coordinates, jump_table_offset, offset_title, \
                page_ids_title, coordinates_title in dictionary_data:
            test_dictionary[hash_value] = [number_ids, offset, jump_table_offset, offset_title]
            test_coordinates[hash_value] = token_coordinates
            test_coordinates_title[hash_value] = coordinates_title

        test_straight_index = dict()
        for page_id, link, title, offset in straight_index_data:
            test_straight_index[page_id] = [link, title, offset]

        return test_dictionary, test_straight_index, dictionary, test_coordinates, test_coordinates_title
    if stats:
        return dictionary


def read_dictionary(dictionary_file_name):
    data = open(dictionary_file_name, 'rb')
    result = dict()

    uncompress_data = zlib.decompress(data.read())

    length_data = len(uncompress_data)
    i = 0
    element_length = HASH_LENGTH+4*INTEGER_LENGTH
    while i < length_data:
        hash_value, number_ids, offset, jump_table_offset, \
            offset_title = struct.unpack(str(HASH_LENGTH)+'siiii', uncompress_data[i:i+element_length])
        result[hash_value.decode('utf-8')] = [number_ids, offset, jump_table_offset, offset_title]
        i += element_length

    data.close()
    return result


def read_page_ids(inverse_index_file_name, offset, number_ids=None):
    if offset == -1:
        return []

    data = open(inverse_index_file_name, 'rb')
    data.seek(offset)

    first_page_id, compressed_page_ids_length = struct.unpack('ii', data.read(2*INTEGER_LENGTH))
    if compressed_page_ids_length < 0:
        print(first_page_id, compressed_page_ids_length, offset)
    page_ids_difference = simple9_decode(data.read(compressed_page_ids_length))
    first_coordinate_offset, compressed_coordinate_offset_length = struct.unpack('ii', data.read(2*INTEGER_LENGTH))
    coordinate_offset_difference = simple9_decode(data.read(compressed_coordinate_offset_length))
    result = [[first_page_id, first_coordinate_offset]]

    for page_id_diff, coordinate_offset_diff in list(zip(page_ids_difference, coordinate_offset_difference)):
        result.append([result[-1][0]+page_id_diff, result[-1][1]+coordinate_offset_diff])

    data.close()

    return result


def read_coordinates(coordinate_file_name, offset):
    data = open(coordinate_file_name, 'rb')
    data.seek(offset)

    _, result, compression_data_length = struct.unpack('iii', data.read(3*INTEGER_LENGTH))
    result = [result]

    if compression_data_length > 0:
        coordinates_difference = simple9_decode(data.read(compression_data_length))
        for difference in coordinates_difference:
            result.append(result[-1] + difference)

    data.close()

    return result


def read_number_coordinates(coordinate_file_name, offset):
    data = open(coordinate_file_name, 'rb')
    data.seek(offset)

    result = struct.unpack('i', data.read(INTEGER_LENGTH))[0]

    data.close()

    return result


def read_first_coordinate(coordinate_file_name, offset):
    data = open(coordinate_file_name, 'rb')
    data.seek(offset)

    result = struct.unpack('ii', data.read(2*INTEGER_LENGTH))[1]

    data.close()

    return result


def read_straight_index(straight_index_file):
    data = open(straight_index_file, 'rb')
    straight_index = dict()

    uncompress_data = zlib.decompress(data.read())

    length_data = len(uncompress_data)
    i = 0
    while i < length_data:
        page_id, state_offset, link_length, title_length = struct.unpack('iiii', uncompress_data[i:i+4*INTEGER_LENGTH])
        i += 4*INTEGER_LENGTH
        link, title = struct.unpack(str(link_length) + 's' + str(title_length) + 's',
                                    uncompress_data[i:i+link_length+title_length])
        straight_index[page_id] = [link.decode('utf-8'), title.decode('utf-8'), state_offset]
        i += link_length+title_length
    data.close()
    return straight_index


def create_all_page_ids(token_file_name, all_page_ids_file_name):
    token_file = open(token_file_name, 'r', encoding='utf-8')
    all_page_ids_file = open(all_page_ids_file_name, 'wb')
    all_page_ids = []

    number_terms = 0
    for line in token_file:
        if line.startswith(PAGE_TOKEN_PREFIX):
            line = line.replace(PAGE_TOKEN_PREFIX, '')
            id_page = int(line)

            if len(all_page_ids) > 0:
                all_page_ids[-1] = [all_page_ids[-1], number_terms]

            number_terms = 0
            all_page_ids.append(id_page)
        else:
            number_terms += len(line.split())

    all_page_ids[-1] = [all_page_ids[-1], number_terms]

    all_page_ids.sort(key=lambda a: a[0])
    for page_id, terms_counter in all_page_ids:
        all_page_ids_file.write(struct.pack('ii', page_id, terms_counter))

    token_file.close()
    all_page_ids_file.close()


def read_all_page_ids(all_page_ids_file_name):
    all_page_ids_file = open(all_page_ids_file_name, 'rb')

    page_ids = []
    for buffer in iter(lambda: all_page_ids_file.read(2*INTEGER_LENGTH), b''):
        if buffer == b'':
            break
        page_ids.append(struct.unpack('ii', buffer)[0])

    all_page_ids_file.close()

    return page_ids


def read_all_page_ids_with_stat(all_page_ids_file_name):
    all_page_ids_file = open(all_page_ids_file_name, 'rb')

    page_ids_with_stat = dict()
    for buffer in iter(lambda: all_page_ids_file.read(2*INTEGER_LENGTH), b''):
        if buffer == b'':
            break
        page_id, terms_number = list(struct.unpack('ii', buffer))
        page_ids_with_stat[page_id] = terms_number

    all_page_ids_file.close()

    return page_ids_with_stat


def union_ids(a, b, inverse_index_file_name):
    result = []

    if not a[0] and not b[0]:
        a = a[1]
        b = b[1]
    elif a[0] and b[0]:
        a = [x for x, y in read_page_ids(inverse_index_file_name, a[2], None)]
        b = [x for x, y in read_page_ids(inverse_index_file_name, b[2], None)]
    elif a[0]:
        a = [x for x, y in read_page_ids(inverse_index_file_name, a[2], None)]
        b = b[1]
    else:
        b = [x for x, y in read_page_ids(inverse_index_file_name, b[2], None)]
        a = a[1]

    n, m = len(a), len(b)
    i, j = 0, 0

    while i < n and j < m:
        if a[i] < b[j]:
            result.append(a[i])
            i += 1
        elif b[j] < a[i]:
            result.append(b[j])
            j += 1
        else:
            result.append(a[i])
            i += 1
            j += 1

    if i < n:
        result.extend(a[i:])
    if j < m:
        result.extend(b[j:])

    return result


def intersection_ids(a, b, inverse_index_file_name):
    result = []

    if not a[0] and not b[0]:
        a = a[1]
        b = b[1]

        n, m = len(a), len(b)
        i, j = 0, 0

        while i < n and j < m:
            if a[i] < b[j]:
                i += 1
            elif b[j] < a[i]:
                j += 1
            else:
                result.append(a[i])
                i += 1
                j += 1
    elif a[0] and b[0]:
        a = [x for x, y in read_page_ids(inverse_index_file_name, a[2])]
        b = [x for x, y in read_page_ids(inverse_index_file_name, b[2])]

        n, m = len(a), len(b)
        i, j = 0, 0

        while i < n and j < m:
            if a[i] < b[j]:
                i += 1
            elif b[j] < a[i]:
                j += 1
            else:
                result.append(a[i])
                i += 1
                j += 1
    else:
        if b[0]:
            a, b = b, a
        inverse_offset = a[2]
        a = a[1]
        b = b[1]
        n, m = len(a), len(b)
        i, j = 0, 0
        while i < n and j < m:
            if a[i][0] < b[j]:
                i += 1
            elif b[j] < a[i][0]:
                block_page_ids = read_block_page_ids(a, i - 1, inverse_index_file_name, inverse_offset)
                k = 0
                while k < len(block_page_ids) and j < m:
                    if block_page_ids[k] < b[j]:
                        k += 1
                    elif b[j] < block_page_ids[k]:
                        j += 1
                    else:
                        result.append(block_page_ids[k])
                        k += 1
                        j += 1
                i += 1
            else:
                result.append(a[i][0])
                i += 1
                j += 1

        last_block_page_ids = read_block_page_ids(a, len(a)-1, inverse_index_file_name, inverse_offset)
        k = 0
        while k < len(last_block_page_ids) and j < m:
            if last_block_page_ids[k] < b[j]:
                k += 1
            elif b[j] < last_block_page_ids[k]:
                j += 1
            else:
                result.append(last_block_page_ids[k])
                k += 1
                j += 1

    return result


def difference_ids(a, b, inverse_index_file_name):
    result = []

    if not a[0] and not b[0]:
        a = a[1]
        b = b[1]
    elif a[0] and b[0]:
        a = [x for x, y in read_page_ids(inverse_index_file_name, a[2], None)]
        b = [x for x, y in read_page_ids(inverse_index_file_name, b[2], None)]
    elif a[0]:
        a = [x for x, y in read_page_ids(inverse_index_file_name, a[2], None)]
        b = b[1]
    else:
        b = [x for x, y in read_page_ids(inverse_index_file_name, b[2], None)]
        a = a[1]

    n, m = len(a), len(b)
    i, j = 0, 0

    while i < n and j < m:
        if a[i] < b[j]:
            result.append(a[i])
            i += 1
        elif b[j] < a[i]:
            j += 1
        else:
            i += 1
            j += 1

    if i < n:
        result.extend(a[i:])

    return result


class TokenType:
    UNKNOWN = -1
    LEXEME = 0
    QUOTE = 1
    OPERATOR_BIN = 2
    OPERATOR_UNO = 3
    OPEN_BRACKET_ROUNDED = 4
    OPEN_BRACKET_FIGURE = 5
    OPEN_BRACKET_SQUARE = 6
    CLOSE_BRACKET_ROUNDED = 7
    CLOSE_BRACKET_FIGURE = 8
    CLOSE_BRACKET_SQUARE = 9


def get_RPN_by_request(user_request):
    user_request = user_request.lower()
    request = []
    for i in range(len(user_request)):
        if not (user_request[i].isdigit() or user_request[i].isalpha() or
                user_request[i] in [')', ']', '}', '(', '[', '{', '&', '|', '!', '"', '/']):
            request.append(' ')
        else:
            request.append(user_request[i])
    request = ''.join(request)
    position = [0]
    last_token_type = [-1]

    def get_next_token():
        while True:
            if position[0] >= len(request):
                return None, None

            if (request[position[0]].isalpha() or request[position[0]].isdigit()) and last_token_type[0] == TokenType.QUOTE:
                last_token_type[0] = TokenType.OPERATOR_BIN
                return TokenType.OPERATOR_BIN, '&&'
            if request[position[0]].isalpha() or request[position[0]].isdigit():
                token = ''
                while position[0] < len(request) and (request[position[0]].isalpha() or request[position[0]].isdigit()):
                    token += request[position[0]].lower()
                    position[0] += 1
                last_token_type[0] = TokenType.LEXEME
                return TokenType.LEXEME, token
            if request[position[0]].isspace() and (last_token_type[0] == TokenType.LEXEME
                                                   or last_token_type[0] == TokenType.QUOTE
                                                   or last_token_type[0] >= TokenType.CLOSE_BRACKET_ROUNDED):
                while position[0] < len(request) and request[position[0]].isspace():
                    position[0] += 1
                if position[0] < len(request) and (request[position[0]].isalpha() or request[position[0]].isdigit() or
                                                           request[position[0]] in ['(', '[', '{', '!', '"']):
                    last_token_type[0] = TokenType.OPERATOR_BIN
                    return TokenType.OPERATOR_BIN, '&&'
                if position[0] >= len(request):
                    return None, None
            if request[position[0]].isspace():
                while position[0] < len(request) and request[position[0]].isspace():
                    position[0] += 1
                if position[0] >= len(request):
                    return None, None
            if position[0]+1 < len(request) and request[position[0]] == '&' and request[position[0]+1] == '&':
                position[0] += 2

                last_token_type[0] = TokenType.OPERATOR_BIN
                return TokenType.OPERATOR_BIN, '&&'
            elif request[position[0]] == '&':
                return TokenType.UNKNOWN, None
            if position[0] + 1 < len(request) and request[position[0]] == '|' and request[position[0] + 1] == '|':
                position[0] += 2
                last_token_type[0] = TokenType.OPERATOR_BIN
                return TokenType.OPERATOR_BIN, '||'
            elif request[position[0]] == '|':
                return TokenType.UNKNOWN, None
            if request[position[0]] == '!':
                position[0] += 1
                last_token_type[0] = TokenType.OPERATOR_UNO
                return TokenType.OPERATOR_UNO, '!'
            if request[position[0]] == '(':
                position[0] += 1
                last_token_type[0] = TokenType.OPEN_BRACKET_ROUNDED
                return TokenType.OPEN_BRACKET_ROUNDED, '('
            if request[position[0]] == '[':
                position[0] += 1
                last_token_type[0] = TokenType.OPEN_BRACKET_SQUARE
                return TokenType.OPEN_BRACKET_SQUARE, '['
            if request[position[0]] == '{':
                position[0] += 1
                last_token_type[0] = TokenType.OPEN_BRACKET_FIGURE
                return TokenType.OPEN_BRACKET_FIGURE, '{'
            if request[position[0]] == ')':
                position[0] += 1
                last_token_type[0] = TokenType.CLOSE_BRACKET_ROUNDED
                return TokenType.CLOSE_BRACKET_ROUNDED, ')'
            if request[position[0]] == '}':
                position[0] += 1
                last_token_type[0] = TokenType.CLOSE_BRACKET_FIGURE
                return TokenType.CLOSE_BRACKET_FIGURE, '}'
            if request[position[0]] == ']':
                position[0] += 1
                last_token_type[0] = TokenType.CLOSE_BRACKET_SQUARE
                return TokenType.CLOSE_BRACKET_SQUARE, ']'
            if request[position[0]] == '"':
                start = position[0] + 1
                position[0] += 1
                while position[0] < len(request) and request[position[0]] != '"':
                    if not (request[position[0]].isalpha() or request[position[0]].isdigit()
                            or request[position[0]].isspace()):
                        return TokenType.UNKNOWN, None
                    position[0] += 1
                if position[0] >= len(request):
                    return TokenType.UNKNOWN, None
                lexemes = request[start:position[0]].split()

                if len(lexemes) == 0:
                    return TokenType.UNKNOWN, None

                distance = len(lexemes) - 1
                position[0] += 1
                space = False
                free_space_after = False
                while position[0] < len(request) and request[position[0]].isspace():
                    space = True
                    position[0] += 1
                if position[0] < len(request) and request[position[0]] == '/':
                    position[0] += 1
                    while position[0] < len(request) and request[position[0]].isspace():
                        position[0] += 1
                        free_space_after = True
                    if position[0] >= len(request) or not request[position[0]].isdigit():
                        return TokenType.UNKNOWN, None
                    start_digit = position[0]
                    while position[0] < len(request) and request[position[0]].isdigit():
                        position[0] += 1
                    if position[0] >= len(request):
                        distance = int(request[start_digit:])
                    elif request[position[0]].isspace() or request[position[0]] in ['&', '|', '(', '[',
                                                                                    '{', ')', ']', '}']:
                        distance = int(request[start_digit:position[0]])
                    else:
                        return TokenType.UNKNOWN, None
                    if distance < len(lexemes) - 1:
                        return TokenType.UNKNOWN, None
                elif position[0] < len(request) and not space and request[position[0]] not in ['|', '&']:
                    return TokenType.UNKNOWN, None
                elif space or free_space_after:
                    position[0] -= 1

                last_token_type[0] = TokenType.QUOTE
                return TokenType.QUOTE, [lexemes, distance]

    result = []
    stack = []
    previous_token_type = -1
    while position[0] < len(request):
        previous_token_type = last_token_type[0]
        token_type, token_value = get_next_token()

        if token_type is None:
            break
        if token_type == TokenType.UNKNOWN:
            return None
        if token_type == TokenType.OPERATOR_BIN and previous_token_type == TokenType.OPERATOR_BIN:
            return None
        if token_type == TokenType.OPERATOR_BIN and previous_token_type == -1:
            return None
        if token_type == TokenType.LEXEME or token_type == TokenType.QUOTE:
            result.append([token_type, token_value])
        elif token_type == TokenType.OPERATOR_UNO:
            stack.append([token_type, token_value])
        elif token_type >= TokenType.OPEN_BRACKET_ROUNDED and token_type <= TokenType.OPEN_BRACKET_SQUARE:
            stack.append([token_type, token_value])
        elif token_type >= TokenType.CLOSE_BRACKET_ROUNDED and token_type <= TokenType.CLOSE_BRACKET_SQUARE:
            while len(stack) > 0 and stack[-1][0] != token_type - 3:
                top_type, top_value = stack.pop()
                if top_type >= TokenType.OPEN_BRACKET_ROUNDED and top_type <= TokenType.OPEN_BRACKET_SQUARE:
                    return None
                result.append([top_type, top_value])
            if len(stack) == 0:
                return None
            stack.pop()
        elif token_type == TokenType.OPERATOR_BIN:
            while len(stack) > 0 and (stack[-1][0] == TokenType.OPERATOR_UNO or stack[-1][1] == token_value
                                      or (stack[-1][1] == '&&' and token_value == '||')):
                result.append(stack.pop())
            stack.append([token_type, token_value])
    if last_token_type[0] == TokenType.OPERATOR_BIN or last_token_type[0] == TokenType.OPERATOR_UNO:
        return None
    while len(stack) > 0:
        if stack[-1][0] == TokenType.OPERATOR_BIN or stack[-1][0] == TokenType.OPERATOR_UNO:
            result.append(stack.pop())
        else:
            return None

    return result


def positional_intersect_ids(data, p, coordinate_index_file_name):
    token_number = len(data)

    if token_number == 1:
        return [x for x, y in data[0]]

    intersect = data[0]
    for k in range(1, token_number):
        temp = []
        n, m = len(intersect), len(data[k])
        i, j = 0, 0

        while i < n and j < m:
            if intersect[i][0] < data[k][j][0]:
                i += 1
            elif data[k][j][0] < intersect[i][0]:
                j += 1
            else:
                page_id = intersect[i][0]
                offsets = intersect[i][1]

                if k == 1:
                    offsets = [offsets]

                offsets.append(data[k][j][1])
                temp.append([page_id, offsets])

                i += 1
                j += 1

        intersect = temp

    result = []
    for page_id, offsets in intersect:
        coordinates = []
        for offset in offsets:
            coordinates.append(read_coordinates(coordinate_index_file_name, offset))

        indexes = [0] * token_number
        while True:
            final = False
            for i in range(token_number):
                if indexes[i] >= len(coordinates[i]):
                    final = True
                    break

            if final:
                break

            i = 0
            another_token_number = p - token_number + 1
            while i < token_number - 1:
                while indexes[i] < len(coordinates[i]) and indexes[i+1] < len(coordinates[i+1]):
                    if coordinates[i+1][indexes[i+1]] - coordinates[i][indexes[i]] > another_token_number + 1:
                        indexes[i] += 1
                    elif coordinates[i][indexes[i]] >= coordinates[i+1][indexes[i+1]]:
                        indexes[i+1] += 1
                    else:
                        distance = coordinates[i+1][indexes[i+1]] - coordinates[i][indexes[i]]
                        another_token_number -= distance - 1
                        i += 1
                        break
                if i < token_number - 1 and (indexes[i] >= len(coordinates[i]) or indexes[i+1] >= len(coordinates[i+1])):
                    break

            if i == token_number - 1:
                result.append(page_id)
                break

    return result


def get_page_ids_by_request(request, dictionary, inverse_index_file_name,
                            all_page_ids, coordinate_index_file_name, jump_table_file_name,
                            inverse_index_title_file_name, coordinate_index_title_file_name):
    rpn = get_RPN_by_request(request)
    stack = []
    stack_title = []
    for token_type, token_value in rpn:
        if token_type == TokenType.LEXEME:
            hash_token = hash_used(remove_rus_ending(token_value))
            if hash_token not in dictionary.keys():
                stack.append([False, []])
            else:
                number_ids, offset, jump_table_offset, offset_title = dictionary[hash_token]
                if jump_table_offset == -1:
                    stack.append([False, [x for x, y in read_page_ids(inverse_index_file_name, offset, number_ids)]])
                else:
                    stack.append([True, read_jump_table(jump_table_file_name, jump_table_offset), offset])
                stack_title.append([False, [x for x, y in read_page_ids(inverse_index_title_file_name, offset_title)]])
        elif token_type == TokenType.QUOTE:
            data = []
            data_title = []
            is_all_tokens = True
            for token in token_value[0]:
                hash_token = hash_used(remove_rus_ending(token))
                if hash_token not in dictionary:
                    stack.append([False, []])
                    stack_title.append([False, []])
                    is_all_tokens = False
                    break
                number_ids, offset, jump_table_offset, offset_title = dictionary[hash_token]
                data.append(read_page_ids(inverse_index_file_name, offset))
                data_title.append(read_page_ids(inverse_index_title_file_name, offset_title))
            if is_all_tokens:
                stack.append([False, positional_intersect_ids(data, token_value[1], coordinate_index_file_name)])
                stack_title.append([False, positional_intersect_ids(data_title, token_value[1],
                                                                    coordinate_index_title_file_name)])
        elif token_type == TokenType.OPERATOR_UNO:
            if len(stack) == 0:
                return None
            value = stack.pop()
            value_title = stack_title.pop()
            if token_value == '!':
                stack.append([False, difference_ids([False, all_page_ids], value, inverse_index_file_name)])
                stack_title.append([False, difference_ids([False, all_page_ids], value_title,
                                                          inverse_index_title_file_name)])
            else:
                return None
        elif token_type == TokenType.OPERATOR_BIN:
            if len(stack) < 2:
                return None
            value_a = stack.pop()
            value_b = stack.pop()
            value_a_title = stack_title.pop()
            value_b_title = stack_title.pop()

            if token_value == '&&':
                stack.append([False, intersection_ids(value_a, value_b, inverse_index_file_name)])
                stack_title.append([False, intersection_ids(value_a_title, value_b_title, inverse_index_title_file_name)])
            elif token_value == '||':
                stack.append([False, union_ids(value_a, value_b, inverse_index_file_name)])
                stack_title.append([False, union_ids(value_a_title, value_b_title, inverse_index_title_file_name)])
            else:
                return None
        else:
            return None

    if len(stack) != 1 or len(stack_title) != 1:
        return None

    if stack[0][0]:
        return [x for x, y in read_page_ids(inverse_index_file_name, stack[0][2])]

    return [stack[0][1], stack_title[0][1]]


def get_SERP_by_request(request, dictionary, inverse_index_file_name, all_page_ids,
                        straight_index, coordinate_index_file_name, jump_table_file_name,
                        all_page_ids_with_stat, token_file_name, inverse_index_title_file_name,
                        coordinate_index_title_file_name, result_offset=0, states_per_page=STATES_NUMBER_IN_SERP):
    terms = ''
    is_boolean_request = False
    for i in range(len(request)):
        if request[i].isalpha() or request[i].isdigit():
            terms += request[i]
        else:
            terms += ' '
        if request[i] in ['&', '|', '(', '[', '{', ')', ']', '}', '!', '"']:
            is_boolean_request = True
    terms = terms.lower()
    terms = [remove_rus_ending(t) for t in terms.split()]

    page_ids = [False, []]
    page_ids_title = [False, []]
    if is_boolean_request:
        page_ids, page_ids_title = get_page_ids_by_request(request, dictionary, inverse_index_file_name, all_page_ids,
                                                           coordinate_index_file_name, jump_table_file_name,
                                                           inverse_index_title_file_name,
                                                           coordinate_index_title_file_name)
    else:
        for term in terms:
            term_hash = hash_used(term)
            if term_hash not in dictionary.keys():
                continue
            page_ids = [False, union_ids(page_ids,
                                        [False, [x for x,y in read_page_ids(inverse_index_file_name,
                                                                            dictionary[term_hash][1])]],
                                         inverse_index_file_name)]
            page_ids_title = [False, union_ids(page_ids,
                                        [False, [x for x,y in read_page_ids(inverse_index_title_file_name,
                                                                            dictionary[term_hash][3])]],
                                           inverse_index_title_file_name)]
        page_ids = page_ids[1]
        page_ids_title = page_ids_title[1]

    collection_length = len(all_page_ids)

    if (page_ids is None and page_ids_title is None) or (len(page_ids) == 0 and len(page_ids_title)):
        return None

    page_ids = [[x, 0.0] for x in page_ids]
    page_ids_title = [[x, 0.0] for x in page_ids_title]

    for term in terms:
        term_hash = hash_used(term)
        if term_hash not in dictionary.keys():
            continue

        number_ids, offset, jump_table_offset, offset_title = dictionary[term_hash]
        page_ids_info = read_page_ids(inverse_index_file_name, offset)
        for_bisect = [x for x, y in page_ids_info]
        page_ids_info_title = read_page_ids(inverse_index_title_file_name, offset_title)
        for_bisect_title = [x for x, y in page_ids_info_title]

        if len(page_ids_info) > 0:
            for i in range(len(page_ids)):
                index_page_id = bisect.bisect_left(for_bisect, page_ids[i][0])
                term_entering_number = 0
                if index_page_id < len(page_ids_info) and page_ids_info[index_page_id][0] == page_ids[i][0]:
                    term_entering_number = read_number_coordinates(coordinate_index_file_name,
                                                                   page_ids_info[index_page_id][1])
                page_ids[i][1] += ((term_entering_number / all_page_ids_with_stat[page_ids[i][0]]) *
                                   math.log2(collection_length / len(page_ids_info))) * (1.0 - TITLE_TF_IDF_WEIGHT)
        if len(page_ids_info_title) > 0:
            for i in range(len(page_ids_title)):
                index_page_id_title = bisect.bisect_left(for_bisect_title, page_ids_title[i][0])
                term_entering_number = 0
                if index_page_id_title < len(page_ids_info_title) and \
                        page_ids_info_title[index_page_id_title][0] == page_ids_title[i][0]:
                    term_entering_number = read_number_coordinates(coordinate_index_title_file_name,
                                                                   page_ids_info_title[index_page_id_title][1])
                page_ids_title[i][1] += (term_entering_number /
                                         len(straight_index[page_ids_title[i][0]][1].split())) * \
                                        math.log2(collection_length / len(page_ids_info_title)) * TITLE_TF_IDF_WEIGHT

    page_ids_result = []
    index_i, index_j = 0, 0
    while index_i < len(page_ids) and index_j < len(page_ids_title):
        if page_ids[index_i][0] == page_ids_title[index_j][0]:
            page_ids_result.append([page_ids[index_i][0], page_ids[index_i][1]*(1.0-TITLE_TF_IDF_WEIGHT)+
                                    page_ids_title[index_j][1]*TITLE_TF_IDF_WEIGHT])
            index_i += 1
            index_j += 1
        elif page_ids[index_i][0] > page_ids_title[index_j][0]:
            page_ids_result.append([page_ids_title[index_i][0], page_ids_title[index_j][1]*TITLE_TF_IDF_WEIGHT])
            index_j += 1
        else:
            page_ids_result.append([page_ids[index_i][0], page_ids[index_i][1] * (1.0 - TITLE_TF_IDF_WEIGHT)])
            index_i += 1
    while index_i < len(page_ids):
        page_ids_result.append([page_ids[index_i][0], page_ids[index_i][1] * (1.0 - TITLE_TF_IDF_WEIGHT)])
        index_i += 1
    while index_j < len(page_ids_title):
        page_ids_result.append([page_ids_title[index_i][0], page_ids_title[index_j][1] * TITLE_TF_IDF_WEIGHT])
        index_j += 1

    page_ids = page_ids_result
    total_states = len(page_ids)
    page_ids.sort(key=lambda a: a[1], reverse=True)
    page_ids = page_ids[result_offset:result_offset+states_per_page]
    first_coordinates = dict()
    for term in terms:
        term_hash = hash_used(term)
        if term_hash not in dictionary.keys():
            continue

        number_ids, offset, jump_table_offset, _ = dictionary[term_hash]
        page_ids_info = read_page_ids(inverse_index_file_name, offset)
        for_bisect = [x for x, y in page_ids_info]

        for page_id, _ in page_ids:
            index_page_id = bisect.bisect_left(for_bisect, page_id)
            if index_page_id < len(page_ids_info) and page_ids_info[index_page_id][0] == page_id:
                first_coordinate = read_first_coordinate(coordinate_index_file_name, page_ids_info[index_page_id][1])
                if page_id not in first_coordinates.keys():
                    first_coordinates[page_id] = [first_coordinate]
                else:
                    first_coordinates[page_id].append(first_coordinate)

    serp = []
    for page_id, _ in page_ids:
        link, title, state_offset = straight_index[page_id]
        page_data = read_page_by_id(token_file_name, straight_index, page_id)[len(title.split()):]
        description = []
        last_added_coordinate = -1
        first_coordinates[page_id].sort()
        line_length = 0
        line_number = 0

        for first_coordinate in first_coordinates[page_id]:
            old_length = len(description)
            if last_added_coordinate >= max(first_coordinate - SNIPPET_WINDOW_SIZE, 0):
                description.append(' '.join(page_data[last_added_coordinate+1:first_coordinate+SNIPPET_WINDOW_SIZE+1]))
            else:
                description.append('... ' + ' '.join(page_data[max(first_coordinate - SNIPPET_WINDOW_SIZE, 0):
                                                               first_coordinate + SNIPPET_WINDOW_SIZE + 1]))
            line_length += len(description) - old_length
            if line_length >= SNIPPET_LINE_LENGTH:
                description.append('\n')
                line_number += 1
                line_length = 0
            if line_number >= SNIPPET_LINE_NUMBER:
                break
            description.append(' ')
            last_added_coordinate = first_coordinate + SNIPPET_WINDOW_SIZE

        serp.append([title, link, ''.join(description)])
    return serp, total_states


class Simple9Schemes:
    SCHEME_1 = [0, 1, 28]
    SCHEME_2 = [1, 2, 14]
    SCHEME_3 = [2, 3, 9]
    SCHEME_4 = [3, 4, 7]
    SCHEME_5 = [4, 5, 5]
    SCHEME_6 = [5, 7, 4]
    SCHEME_7 = [6, 9, 3]
    SCHEME_8 = [7, 14, 2]
    SCHEME_9 = [8, 28, 1]
    ALL_SCHEMES = [SCHEME_9, SCHEME_8, SCHEME_7, SCHEME_6, SCHEME_5, SCHEME_4, SCHEME_3, SCHEME_2, SCHEME_1]


def simple9_encode(sequence, jump_table_info_need=False):
    result = bytearray()
    n = len(sequence)
    i = 0
    jump_table_info = []
    used_byte_counter = 0
    while i < n:
        for scheme in Simple9Schemes.ALL_SCHEMES:
            code, number_elements, bit_length = scheme
            if i + (number_elements - 1) >= n:
                continue
            ok = True
            for j in range(number_elements):
                if sequence[i+j] > 2**bit_length - 1:
                    ok = False
                    break

            if ok:
                data = code
                data <<= (28-number_elements*bit_length)
                for j in range(number_elements):
                    data <<= bit_length
                    data |= sequence[i+j]

                if jump_table_info_need and used_byte_counter > 0 and used_byte_counter % JUMP_TABLE_SPACE_BYTES == 0:
                    jump_table_info.append([i, used_byte_counter])

                result.extend(data.to_bytes(4, 'big'))
                used_byte_counter += 4
                i += number_elements

    if jump_table_info_need:
        return result, jump_table_info

    return result


def simple9_decode(data):
    result = []
    i = 0
    n = len(data)
    while i < n:
        buffer = int.from_bytes(data[i:i+4], 'big', signed=False)
        code = (buffer >> 28)
        _, number_elements, bit_length = Simple9Schemes.ALL_SCHEMES[-(code+1)]
        mask = (1 << bit_length)-1
        numbers = [0] * number_elements
        for j in range(number_elements):
            numbers[number_elements-(j+1)] = (buffer & mask)
            buffer >>= bit_length
        result.extend(numbers)
        i += 4

    return result


def read_jump_table(jump_table_file_name, offset):
    data = open(jump_table_file_name, 'rb')
    data.seek(offset)

    first_page_id, compressed_page_ids_length = struct.unpack('ii', data.read(2*INTEGER_LENGTH))
    page_ids_difference = simple9_decode(data.read(compressed_page_ids_length))
    first_offset, compressed_coordinate_offset_length = struct.unpack('ii', data.read(2*INTEGER_LENGTH))
    offset_difference = simple9_decode(data.read(compressed_coordinate_offset_length))
    result = [[first_page_id, first_offset]]

    for page_id_diff, offset_diff in list(zip(page_ids_difference, offset_difference)):
        result.append([result[-1][0]+page_id_diff, result[-1][1]+offset_diff])

    data.close()

    return result


def read_first_page_id_and_length_compress_data(inverse_index_file_name, offset):
    data = open(inverse_index_file_name, 'rb')
    data.seek(offset)

    first_page_id, length_compress_data = struct.unpack('ii', data.read(INTEGER_LENGTH*2))

    data.close()

    return first_page_id, length_compress_data


def read_block_page_ids(jump_table, block_id, inverse_index_file_name, offset_inverse_index):
    data = open(inverse_index_file_name, 'rb')
    result = []

    first_page_id, length_compress_data = read_first_page_id_and_length_compress_data(inverse_index_file_name,
                                                                                      offset_inverse_index)

    if block_id == -1:
        result.append(first_page_id)
        offset_inverse_index += INTEGER_LENGTH * 2

        data.seek(offset_inverse_index)
        differences_page_ids = simple9_decode(data.read(JUMP_TABLE_SPACE_BYTES))

        for page_id_diff in differences_page_ids:
            result.append(result[-1]+page_id_diff)
    else:
        block_first_page_id, block_offset_inverse_index = jump_table[block_id]
        result.append(block_first_page_id)

        data.seek(block_offset_inverse_index)
        if block_id == len(jump_table) - 1:
            differences_page_ids = simple9_decode(data.read(length_compress_data - JUMP_TABLE_SPACE_BYTES * (block_id + 1)))[1:]
        else:
            differences_page_ids = simple9_decode(data.read(JUMP_TABLE_SPACE_BYTES))[1:]

        for page_id_diff in differences_page_ids:
            result.append(result[-1]+page_id_diff)

    data.close()

    return result


def remove_rus_ending(word):
    rus_endings_verb = ['ать', 'ять', 'оть', 'еть', 'уть', 'у', 'ю', 'ем', 'им', 'ешь', 'ишь', 'ете', 'ите', 'ет',
                        'ит', 'ут', 'ют', 'ят', 'ал', 'ял', 'ала', 'яла', 'али', 'яли', 'ол', 'ел', 'ола', 'ела',
                        'оли', 'ели', 'ул', 'ула', 'ули']
    rus_endings_name = ['а', 'я', 'о', 'е', 'ь', 'ы', 'и', 'а', 'ая', 'яя', 'ое', 'ее', 'ой', 'ые', 'ие', 'ый', 'йй']
    rus_endings_flex = ['а', 'ам', 'ами', 'ас', 'ам', 'ax', 'ая', 'е', 'её', 'ей', 'ем', 'еми', 'емя', 'ex', 'ею',
                        'ёт', 'ёте', 'ёх', 'ёшь', 'и', 'ие', 'ий', 'им', 'ими', 'ит', 'ите', 'их', 'ишь', 'ию', 'м',
                        'ми', 'мя', 'о', 'ов', 'ого', 'ое', 'оё', 'ой', 'ом', 'ому', 'ою', 'см', 'у', 'ум',
                        'умя', 'ут', 'ух', 'ую', 'шь']

    rus_endings = []
    rus_endings.extend(rus_endings_verb)
    rus_endings.extend(rus_endings_name)
    rus_endings.extend(rus_endings_flex)

    valid_endings = []
    for ending in rus_endings:
        if word.endswith(ending) and len(word) > len(ending):
            valid_endings.append(ending)

    index_ending = -1
    max_length = -1
    for i in range(len(valid_endings)):
        if max_length < len(valid_endings[i]):
            max_length = len(valid_endings[i])
            index_ending = i

    if index_ending == -1:
        return word

    return word[0:len(word)-len(valid_endings[index_ending])]


def read_page_by_id(token_file_name, straight_index, page_id):
    token_file = open(token_file_name, 'r', encoding='utf-8')

    token_file.seek(straight_index[page_id][2])

    result = []
    for line in token_file:
        if line.startswith(PAGE_TOKEN_PREFIX):
            break
        result.extend(line.split())

    return result


class SearchEngine:
    xml_file_name = './core/Википедия-20190226103515.xml'
    data_file_name = './core/data.txt'
    token_file_name = './core/tokens.txt'
    dictionary_file_name = './core/dictionary.bin'
    inverse_index_file_name = './core/inverse_index.bin'
    straight_index_file_name = './core/straight_index.bin'
    all_page_ids_file_name = './core/all_page_ids.bin'
    coordinate_index_file_name = './core/coordinate_index.bin'
    jump_table_file_name = './core/jump_table.bin'
    inverse_index_title_file_name = './core/inverse_title_index.bin'
    coordinate_index_title_file_name = './core/coordinate_title_index.bin'

    def _load(self):
        self.dictionary = read_dictionary(SearchEngine.dictionary_file_name)
        self.straight_index = read_straight_index(SearchEngine.straight_index_file_name)
        self.all_page_ids = read_all_page_ids(SearchEngine.all_page_ids_file_name)
        self.all_page_ids_with_stat = read_all_page_ids_with_stat(SearchEngine.all_page_ids_file_name)

    def __init__(self):
        self._load()

    def SERP(self, request, page, states_per_page):
        start_time = time.time()
        serp, total_states = get_SERP_by_request(request, self.dictionary, SearchEngine.inverse_index_file_name,
                                                 self.all_page_ids, self.straight_index,
                                                 SearchEngine.coordinate_index_file_name,
                                                 SearchEngine.jump_table_file_name, self.all_page_ids_with_stat,
                                                 SearchEngine.token_file_name,
                                                 SearchEngine.inverse_index_title_file_name,
                                                 SearchEngine.coordinate_index_title_file_name,
                                                 (page-1)*states_per_page, states_per_page)
        request_time = time.time() - start_time
        number_pages = (total_states//states_per_page) + (1 if total_states % states_per_page != 0 else 0)
        return serp, request_time, number_pages, total_states

    @staticmethod
    def check_request(request):
        try:
            result = get_RPN_by_request(request)
            if result is None:
                return False
            return True
        except:
            return False

    def create_index(self):
        parse_wiki_xml(SearchEngine.xml_file_name, SearchEngine.data_file_name)
        tokenization(SearchEngine.data_file_name, SearchEngine.token_file_name)
        indexation(SearchEngine.token_file_name, SearchEngine.dictionary_file_name,
                   SearchEngine.inverse_index_file_name, SearchEngine.straight_index_file_name,
                   SearchEngine.coordinate_index_file_name, SearchEngine.jump_table_file_name,
                   SearchEngine.inverse_index_title_file_name, SearchEngine.coordinate_index_title_file_name)

        self._load()

