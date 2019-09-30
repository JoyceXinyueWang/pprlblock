import os
import time
import math
import hashlib
from collections import defaultdict

from pprlindex import PPRLIndex
from config import QGRAM_LEN, QGRAM_PADDING, PADDING_START_CHAR, PADDING_END_CHAR


class PPRLIndexPSignature(PPRLIndex):
    """Class that implements the PPRL indexing technique:

        Reference scalability entity resolution using probability signatures
        on parallel databases.

        This class includes an implmentation of p-sig algorithm.
    """

    def __init__(self, num_hash_funct, bf_len):
        """Initialize the class and set the required parameters.

        Arguments:
        - sigfunc              function that takes one of those values and returns an
                               iterable of potential signatures
        - maximum_block_size   expected recurrence frequency of a signature
        - tao                  the threshold for us to adopt a link if the probability
                               for two records to share a signature exceeds tao
        - rou                  the threshold we consider a subrecord if its probability
                               of being a signature exceeds rou

        """
        self.num_hash_funct = num_hash_funct
        self.bf_len = bf_len
        self.bf_cache = {}
        self.alice_bf = None
        self.bob_bf = None
        self.common_bf = None
        self.ngram_alice_dict = {}
        self.ngram_bob_dict = {}


    def __str2bf__(self, s, do_cache=False):
        """Convert a single string into a Bloom filter (a set with the index
           values of the bits set to 1 according to the given Bloom filter length.

           This method returns the generated Bloom filter as a set.

           If do_cache is set to True then the Bloom filter for this string will
           be stored.
        """
        if (s in self.bf_cache):
          return self.bf_cache[s]

        h1 =             hashlib.sha1
        h2 =             hashlib.md5
        num_hash_funct = self.num_hash_funct

        q_minus_1 = QGRAM_LEN - 1

        if (QGRAM_PADDING == True):
          ps = PADDING_START_CHAR*q_minus_1 + s + PADDING_END_CHAR*q_minus_1
        else:
          ps = s

        q_gram_list = [ps[i:i+QGRAM_LEN] for i in range(len(ps) - q_minus_1)]

        bloom_set = set()

        for q in q_gram_list:

          hex_str1 = h1(q.encode('utf-8')).hexdigest()
          int1 =     int(hex_str1, 16)

          hex_str2 = h2(q.encode('utf-8')).hexdigest()
          int2 =     int(hex_str2, 16)

          for i in range(num_hash_funct):
            gi = int1 + i*int2
            gi = int(gi % self.bf_len)

            bloom_set.add(gi)

        if (do_cache == True):  # Store in cache
         self.bf_cache[s] = bloom_set

        return bloom_set


    def ngram2bf(self, ngram):
        """Convert a ngram to bloom filter set."""
        h1 = hashlib.sha1
        h2 = hashlib.md5
        num_hash_funct = self.num_hash_funct
        hex_str1 = h1(ngram.encode('utf-8')).hexdigest()
        int1 = int(hex_str1, 16)
        hex_str2 = h2(ngram.encode('utf-8')).hexdigest()
        int2 = int(hex_str2, 16)
        bloom_set = set()
        for i in range(num_hash_funct):
            gi = int1 + i * int2
            gi = int(gi % self.bf_len)
            bloom_set.add(gi)
        return bloom_set


    def create_bloom_filter(self, ngrams):
        """Create Bloom filter on set of ngrams."""
        bloom = set()
        for gram in ngrams:
            bloom_set = self.ngram2bf(gram)
            bloom = bloom.union(bloom_set)
        return bloom

    def get_ngram(self, records, ngram_dict, attr_list):
        """Obtain N-gram of selected attributes for all records."""
        ngrams = set()
        for key, rec in records.items():
            value = [rec[x] for x in attr_list]
            ps = ''.join(value)
            q_minus_1 = QGRAM_LEN - 1
            # add each ngram to set
            for i in range(len(ps) - q_minus_1):
                gram = ps[i: i + QGRAM_LEN]
                ngrams.add(gram)
                if gram in ngram_dict:
                    ngram_dict[gram].append(key)
                else:
                    ngram_dict[gram] = [key]
        return ngrams, ngram_dict

    def alice_bloom_filter(self, attr_list):
        """Create bloom filter on Alice's attributes."""
        res = self.get_ngram(self.rec_dict_alice, self.ngram_alice_dict,
                             attr_list)
        ngrams, ngram_dict = res
        bf = self.create_bloom_filter(ngrams)
        self.alice_bf = bf
        self.ngram_alice_dict = ngram_dict
        return bf

    def bob_bloom_filter(self, attr_list):
        """Create bloom filter on Bob's attributes."""
        res = self.get_ngram(self.rec_dict_bob, self.ngram_bob_dict,
                             attr_list)
        ngrams, ngram_dict = res
        bf = self.create_bloom_filter(ngrams)
        self.bob_bf = bf
        self.ngram_bob_dict = ngram_dict
        return bf

    def common_bloom_filter(self, attr_list):
        """Intersect two bloom filter and return."""
        if self.alice_bf is None or self.bob_bf is None:
            self.alice_bloom_filter(attr_list)
            self.bob_bloom_filter(attr_list)
        # take intersection of two sets
        common_bf = self.alice_bf.intersection(self.bob_bf)
        self.common_bf = common_bf
        return common_bf

    def microblocks(self, common_bf, ngram_dict):
        """Construct micro blocks."""
        revert_index = {}
        for ngram, value in ngram_dict.items():
            bf = self.ngram2bf(ngram)
            if bf.intersection(common_bf) == bf:
                revert_index[ngram] = value
        return revert_index

    def build_index_alice(self):
        """Build revert index for alice data."""
        start_time = time.time()
        assert self.rec_dict_alice != None
        assert self.ngram_alice_dict != None
        assert self.common_bf != None
        revert_index = self.microblocks(self.common_bf, self.ngram_alice_dict)
        self.index_alice = revert_index
        alice_time = time.time() - start_time
        stat = self.block_stats(revert_index)
        min_block_size,med_blk_size,max_block_size,avr_block_size,std_dev,blk_len_list = stat
        return min_block_size,med_blk_size,max_block_size,avr_block_size,std_dev

    def build_index_bob(self):
        """Build revert index for alice data."""
        start_time = time.time()
        assert self.rec_dict_bob != None
        assert self.ngram_bob_dict != None
        assert self.common_bf != None
        revert_index = self.microblocks(self.common_bf, self.ngram_bob_dict)
        self.index_bob = revert_index
        bob_time = time.time() - start_time
        stat = self.block_stats(revert_index)
        min_block_size,med_blk_size,max_block_size,avr_block_size,std_dev,blk_len_list = stat
        return min_block_size,med_blk_size,max_block_size,avr_block_size,std_dev

    def generate_blocks(self):
        """Generates blocks based on built two index."""
        block_dict = {}

        index_alice = self.index_alice
        index_bob = self.index_bob

        cand_blk_key = 0
        for (block_id, block_vals) in index_alice.items():
            bob_block_vals = index_bob.get(block_id, None)
            if bob_block_vals != None:
                block_dict[cand_blk_key] = (block_vals, bob_block_vals)
                cand_blk_key += 1
        self.block_dict = block_dict
        print('Final indexing contains %d blocks' % (len(block_dict)))
        return len(block_dict)


# def initials(rec, gname_ind, sname_ind):
#     """Extract initials as signature."""
#     WORDS = re.compile("\w+")
#     name = '{} {}'.format(rec[gname_ind][0], rec[sname_ind][0])
#     init = name
#     return init
#

# oz_small_alice_file_name = './datasets/1730_50_overlap_no_mod_alice.csv.gz'
# oz_small_bob_file_name = './datasets/1730_50_overlap_no_mod_bob.csv.gz'
# psig = PPRLIndexPSignature(num_hash_funct=3, bf_len=1800)
# psig.load_database_alice(oz_small_alice_file_name, header_line=True,
#                        rec_id_col=0, ent_id_col=0)
# psig.load_database_bob(oz_small_bob_file_name, header_line=True,
#                        rec_id_col=0, ent_id_col=0)
# psig.common_bloom_filter([1, 2])
# psig.build_index_alice()
# psig.build_index_bob()
# alice = psig.rec_dict_alice
# rec = alice['3461']
# attr_list = [1, 2]
# value = [rec[x] for x in attr_list]
#
# gramalice = psig.get_ngram(psig.rec_dict_alice, attr_list)
# grambob = psig.get_ngram(psig.rec_dict_bob, attr_list)
#
# balice = psig.alice_bloom_filter(attr_list)
# bbob = psig.bob_bloom_filter(attr_list)
# common_bf = psig.common_bloom_filter(attr_list)
# import IPython; IPython.embed()
